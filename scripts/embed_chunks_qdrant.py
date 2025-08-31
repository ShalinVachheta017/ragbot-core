"""
Batch embeddings of tender documents (PDFs) into Qdrant.
- Extracts ZIPs -> PDFs -> chunks
- Adds payload with: text, source (relative), page, chunk_index, doc_hash, dtad_id
- Uses E5 'passage:' prefix for document embeddings
"""
from __future__ import annotations
import os, sys, zipfile, shutil, logging, hashlib, json, re
from pathlib import Path
from typing import List, Dict
from uuid import uuid4
from logging.handlers import RotatingFileHandler

from tqdm import tqdm
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models

from config import (
    EXTRACT_DIR, ROOT_DIR, EMBED_MODEL_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME, QDRANT_URL
)

# --- Logging -----------------------------------------------------------------
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "embed_chunks_qdrant.log"

fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embed_chunks_qdrant")
fh = RotatingFileHandler(LOG_FILE, maxBytes=10_000_000, backupCount=3, encoding="utf-8")
fh.setFormatter(logging.Formatter(fmt))
fh.setLevel(logging.INFO)
logger.addHandler(fh)

logging.getLogger("qdrant_client").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Settings ----------------------------------------------------------------
RAW_DIR = ROOT_DIR / "data" / "raw"
HASH_FILE = ROOT_DIR / "processed_hashes.json"
BATCH_EMBED = int(os.getenv("BATCH_EMBED", "256"))
BATCH_UPSERT = int(os.getenv("BATCH_UPSERT", "256"))
DTAD_RE = re.compile(r"DTAD[_-]?(\d{8})")

# --- Helpers -----------------------------------------------------------------
def get_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_or_init_hashes() -> set[str]:
    if HASH_FILE.exists():
        try:
            return set(json.loads(HASH_FILE.read_text(encoding="utf-8")))
        except Exception:
            logger.warning("Could not read processed_hashes.json — starting fresh")
    return set()

def save_hashes(hashes: set[str]) -> None:
    HASH_FILE.write_text(json.dumps(sorted(hashes), indent=2), encoding="utf-8")

def pick_device() -> str:
    try:
        import torch  # type: ignore
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"

# --- Main --------------------------------------------------------------------
def main() -> None:
    logger.info("=== Embedding pipeline (Qdrant) starting ===")

    # Qdrant client
    client = QdrantClient(url=QDRANT_URL, prefer_grpc=False)
    client.get_collections()  # fail fast if unreachable
    logger.info(f"Connected to Qdrant at {QDRANT_URL}")

    # Discover ZIPs and (re)extract
    zip_files = sorted(RAW_DIR.rglob("*.zip"))
    logger.info(f"Found {len(zip_files)} zip files recursively under {RAW_DIR}")
    shutil.rmtree(EXTRACT_DIR, ignore_errors=True)
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    for zip_path in tqdm(zip_files, desc="Unzipping ZIPs", unit="zip"):
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(EXTRACT_DIR / zip_path.stem)
        except zipfile.BadZipFile:
            logger.warning(f"Bad zip skipped: {zip_path}")

    # Discover PDFs
    pdf_paths = sorted(EXTRACT_DIR.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_paths)} PDFs to process")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n","\n"," ",""]
    )

    seen_hashes = load_or_init_hashes()
    new_hashes: set[str] = set()
    texts: List[str] = []
    metas: List[Dict] = []

    for pdf_path in tqdm(pdf_paths, desc="Chunking PDFs", unit="pdf"):
        pdf_hash = get_file_hash(pdf_path)
        if pdf_hash in seen_hashes:
            logger.info(f"⏭️  Skip already-embedded PDF: {pdf_path.name}")
            continue

        # derive dtad_id from path (e.g., extractdirect/DTAD_20047454/..)
        rel = str(pdf_path.relative_to(ROOT_DIR))
        m = DTAD_RE.search(rel)
        dtad_id = int(m.group(1)) if m else None

        try:
            pages = PyMuPDFLoader(str(pdf_path)).load()
        except Exception as e:
            logger.warning(f"Failed to read PDF {pdf_path.name}: {e}")
            continue

        chunks = splitter.split_documents(pages)
        for i, ch in enumerate(chunks):
            meta = ch.metadata.copy()
            meta.update({
                "source": rel,                 # keep relative path
                "chunk_index": i,
                "doc_hash": pdf_hash,
                "text": ch.page_content,       # retrieve-only payload
                "page": meta.get("page"),
            })
            if dtad_id is not None:
                meta["dtad_id"] = dtad_id

            texts.append(ch.page_content)
            metas.append(meta)

        new_hashes.add(pdf_hash)

    logger.info(f"Prepared {len(texts)} chunks for embedding")
    if not texts:
        logger.info("Nothing to embed. Exiting.")
        return

    # Embeddings (E5 requires 'passage:' prefix for documents)  ── refs: sbert docs
    device = pick_device()
    logger.info(f"Loading embedding model on device: {device}")
    embedder = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME, model_kwargs={"device": device})
    dim = len(embedder.embed_query("dimension_probe"))
    logger.info(f"Model loaded: {EMBED_MODEL_NAME} (dim={dim})")

    # Ensure collection (create if missing; keep if exists)
    try:
        client.get_collection(COLLECTION_NAME)
        logger.info(f"Collection exists: {COLLECTION_NAME}")
    except Exception:
        logger.info(f"Creating collection: {COLLECTION_NAME}")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            optimizers_config=models.OptimizersConfigDiff(default_segment_number=2),
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=200),
        )

    # Embed & upsert
    total = len(texts)
    upserted = 0
    for i in tqdm(range(0, total, BATCH_EMBED), desc="Embedding", unit="chunk"):
        batch_texts = texts[i:i+BATCH_EMBED]
        batch_metas = metas[i:i+BATCH_EMBED]

        # E5 doc/passage prefix
        vectors = embedder.embed_documents([f"passage: {t}" for t in batch_texts])

        for j in range(0, len(vectors), BATCH_UPSERT):
            vecs = vectors[j:j+BATCH_UPSERT]
            payl = batch_metas[j:j+BATCH_UPSERT]
            points = [models.PointStruct(id=uuid4().hex, vector=v, payload=p) for v, p in zip(vecs, payl)]
            client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
            upserted += len(points)

    logger.info(f"✅ Embedded {upserted} chunks into Qdrant collection: {COLLECTION_NAME}")

    # Save hash cache
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
