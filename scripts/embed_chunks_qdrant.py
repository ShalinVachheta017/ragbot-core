"""
Batch embeddings of tender documents (PDFs) using recursive ZIP extraction,
GPU-accelerated embedding, duplicate skipping using content hash,
and Qdrant vector DB backend.
"""

from __future__ import annotations

import os
import sys
import zipfile
import shutil
import logging
import hashlib
import json
from pathlib import Path
from typing import List, Dict
from uuid import uuid4

from tqdm import tqdm

# ---- LangChain + PDF + Embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ---- Qdrant
from qdrant_client import QdrantClient, models

# ---- Config (project-local)
from .config import (
    EXTRACT_DIR,
    ROOT_DIR,
    EMBED_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

# =============================================================================
# Logging (file + quiet console)
# =============================================================================
from logging.handlers import RotatingFileHandler

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "embed_chunks_qdrant.log"

_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
formatter = logging.Formatter(_fmt)

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=10_000_000, backupCount=3, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # WARN+ to terminal
console_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

logger = logging.getLogger("embed_chunks_qdrant")
logging.getLogger("qdrant_client").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# =============================================================================
# Settings
# =============================================================================
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "tender_chunks")
QDRANT_HOST = os.getenv("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

RAW_DIR = ROOT_DIR / "data" / "raw"
HASH_FILE = ROOT_DIR / "processed_hashes.json"

BATCH_EMBED = int(os.getenv("BATCH_EMBED", "256"))
BATCH_UPSERT = int(os.getenv("BATCH_UPSERT", "256"))

# =============================================================================
# Helpers
# =============================================================================
def get_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_or_init_hashes() -> set[str]:
    if HASH_FILE.exists():
        try:
            with open(HASH_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            logger.warning("Could not read processed_hashes.json — starting fresh")
    return set()


def save_hashes(hashes: set[str]) -> None:
    with open(HASH_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(hashes)), f, indent=2)


def pick_device() -> str:
    try:
        import torch  # type: ignore
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    logger.info("=== Embedding pipeline (Qdrant) starting ===")

    # ----- Qdrant client (fail fast if not reachable)
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, prefer_grpc=False)
    try:
        _ = client.get_collections()
        logger.info(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
    except Exception as e:
        logger.error("Cannot reach Qdrant. Is the container up? (docker compose up -d)")
        raise

    # ----- Find ZIPs
    zip_files = sorted(RAW_DIR.rglob("*.zip"))
    logger.info(f"Found {len(zip_files)} zip files recursively in {RAW_DIR}")

    # ----- Clean + extract
    shutil.rmtree(EXTRACT_DIR, ignore_errors=True)
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    for zip_path in tqdm(zip_files, desc="Unzipping ZIPs", unit="zip"):
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(EXTRACT_DIR / zip_path.stem)
        except zipfile.BadZipFile:
            logger.warning(f"Bad zip skipped: {zip_path}")

    # ----- Discover PDFs
    pdf_paths = sorted(EXTRACT_DIR.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_paths)} PDFs to process")

    # ----- Load/Chunk settings
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )

    # ----- Hash cache (skip already-done PDFs)
    seen_hashes = load_or_init_hashes()
    new_hashes: set[str] = set()

    texts: List[str] = []
    metas: List[Dict] = []

    for pdf_path in tqdm(pdf_paths, desc="Chunking PDFs", unit="pdf"):
        pdf_hash = get_file_hash(pdf_path)
        if pdf_hash in seen_hashes:
            logger.info(f"⏭️  Skip already-embedded PDF: {pdf_path.name}")
            continue

        try:
            pages = PyMuPDFLoader(str(pdf_path)).load()
        except Exception as e:
            logger.warning(f"Failed to read PDF {pdf_path.name}: {e}")
            continue

        chunks = splitter.split_documents(pages)
        for i, ch in enumerate(chunks):
            meta = ch.metadata.copy()
            meta["source"] = str(pdf_path.relative_to(ROOT_DIR))
            meta["chunk_index"] = i
            meta["doc_hash"] = pdf_hash
            meta["text"] = ch.page_content  # keep text in payload for retrieval

            texts.append(ch.page_content)
            metas.append(meta)

        new_hashes.add(pdf_hash)

    logger.info(f"Prepared {len(texts)} chunks for embedding")

    if not texts:
        logger.info("Nothing to embed. Exiting.")
        return

    # ----- Embeddings (GPU if available)
    device = pick_device()
    logger.info(f"Loading embedding model on device: {device}")
    embedder = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL_NAME, model_kwargs={"device": device}
    )
    dim = len(embedder.embed_query("dimension_probe"))
    logger.info(f"Model loaded: {EMBED_MODEL_NAME} (dim={dim})")

    # ----- Ensure collection
    try:
        client.get_collection(COLLECTION_NAME)
        logger.info(f"Collection exists: {COLLECTION_NAME}")
    except Exception:
        logger.info(f"Creating collection: {COLLECTION_NAME}")
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=dim,
                distance=models.Distance.COSINE,
                on_disk=True,  # store vectors on disk for larger-than-RAM
            ),
        )

    # ----- Embed + upsert in batches
    total = len(texts)
    upserted = 0

    for i in tqdm(range(0, total, BATCH_EMBED), desc="Embedding", unit="chunk"):
        batch_texts = texts[i : i + BATCH_EMBED]
        batch_metas = metas[i : i + BATCH_EMBED]

        vectors = embedder.embed_documents(batch_texts)

        # upsert in smaller shards if you like
        for j in range(0, len(vectors), BATCH_UPSERT):
            vecs = vectors[j : j + BATCH_UPSERT]
            payl = batch_metas[j : j + BATCH_UPSERT]

            points = [
                models.PointStruct(id=uuid4().hex, vector=v, payload=p)
                for v, p in zip(vecs, payl)
            ]
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True,
            )

            upserted += len(points)

    logger.info(f"✅ Embedded {upserted} chunks to Qdrant collection: {COLLECTION_NAME}")

    # ----- Save new hashes
    seen_hashes.update(new_hashes)
    save_hashes(seen_hashes)
    logger.info("💾 Updated processed_hashes.json")

    logger.info("=== Embedding pipeline finished ===")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
