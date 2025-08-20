# scripts/embed_chunks_qdrant.py
"""
Embeds PDFs from EXTRACT_DIR into Qdrant.
Adds Excel fields to payload if metadata/cleaned_metadata.xlsx exists.
Logs -> logs/embed_chunks_qdrant.log
Env flags:
  FORCE_REEMBED=1  (ignore processed_hashes.json and re-embed)
"""

import os
import json
import time
import hashlib
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid


import fitz  # PyMuPDF
from tqdm import tqdm
from langdetect import detect
from sentence_transformers import SentenceTransformer
import pandas as pd

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# ---------- Logging ----------
LOG_DIR = Path("logs"); LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "embed_chunks_qdrant.log"

logger = logging.getLogger("embed_qdrant")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=7, encoding="utf-8")
    fh.setFormatter(fmt); fh.setLevel(logging.INFO)
    ch = logging.StreamHandler(); ch.setFormatter(fmt); ch.setLevel(logging.INFO)
    logger.addHandler(fh); logger.addHandler(ch)

# ---------- Config ----------
try:
    from .config import (
        EXTRACT_DIR,
        COLLECTION_NAME as CFG_COLLECTION,
        EMBED_MODEL_NAME as CFG_EMBED,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        CLEANED_EXCEL,
    )
except Exception:
    EXTRACT_DIR = Path("extractdirect")
    CFG_COLLECTION = "tender_docs"
    CFG_EMBED = "intfloat/multilingual-e5-small"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    CLEANED_EXCEL = Path("metadata/cleaned_metadata.xlsx")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", CFG_COLLECTION)
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", CFG_EMBED)
FORCE_REEMBED = bool(int(os.getenv("FORCE_REEMBED", "0")))
BATCH_SIZE = int(os.getenv("EMBED_BATCH", "64"))

PROCESSED_HASHES = Path("processed_hashes.json")

# ---------- Excel metadata ----------
def _normalize_fn(x: str) -> str:
    return Path(str(x)).name.lower()

def _load_excel_map(path: Path) -> Optional[Dict[str, Dict[str, Any]]]:
    try:
        if not path.exists():
            logger.warning("No cleaned Excel at %s (payloads will omit Excel fields)", path)
            return None
        df = pd.read_excel(path) if path.suffix.lower() == ".xlsx" else pd.read_csv(path)
        if "filename" not in df.columns:
            logger.warning("Cleaned Excel missing 'filename'; ignoring.")
            return None
        df.columns = [c.strip() for c in df.columns]
        keep_cols = [c for c in df.columns if c != "filename"]
        mapping = {}
        for _, row in df.iterrows():
            mapping[_normalize_fn(row["filename"])] = {c: row[c] for c in keep_cols}
        logger.info("Loaded Excel metadata rows: %d", len(mapping))
        return mapping
    except Exception as e:
        logger.error("Failed to read cleaned Excel %s: %s", path, e)
        return None

# ---------- Helpers ----------
def load_processed() -> Dict[str, str]:
    if PROCESSED_HASHES.exists():
        try:
            return json.loads(PROCESSED_HASHES.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_processed(d: Dict[str, str]):
    PROCESSED_HASHES.write_text(json.dumps(d, indent=2), encoding="utf-8")

def file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def read_pdf_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts)

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

def ensure_collection(client: QdrantClient, dim: int):
    try:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info("Created collection %s (dim=%s)", COLLECTION_NAME, dim)
    except Exception as e:
        if "exists" in str(e).lower():
            pass
        else:
            raise

def deterministic_point_id(pdf_name: str, doc_hash: str, chunk_index: int) -> str:
    name = f"{pdf_name}|{doc_hash}|{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))  

def upsert_batch(client: QdrantClient, vectors: List[List[float]], payloads: List[Dict[str, Any]]):
    points = []
    for v, pl in zip(vectors, payloads):
        points.append(PointStruct(id=pl["point_id"], vector=v, payload=pl))
    client.upsert(collection_name=COLLECTION_NAME, points=points)

# ---------- Main ----------
def main():
    t0 = time.time()
    extract_dir = Path(EXTRACT_DIR)
    if not extract_dir.exists():
        logger.error("EXTRACT_DIR not found: %s", extract_dir)
        return

    embedder = SentenceTransformer(EMBED_MODEL_NAME)
    dim = embedder.get_sentence_embedding_dimension()
    client = QdrantClient(url=QDRANT_URL)
    ensure_collection(client, dim)

    excel_map = _load_excel_map(Path(CLEANED_EXCEL))

    processed = load_processed()
    pdfs = sorted(extract_dir.rglob("*.pdf"))
    logger.info("Found %d PDFs under %s", len(pdfs), extract_dir.resolve())
    if not pdfs:
        return

    total_chunks = 0
    updated_files = 0
    skipped_files = 0

    for pdf in tqdm(pdfs, desc="Embedding PDFs"):
        h = file_hash(pdf)
        if not FORCE_REEMBED and processed.get(str(pdf)) == h:
            skipped_files += 1
            logger.info("Skip unchanged: %s", pdf.name)
            continue

        try:
            text = read_pdf_text(pdf)
        except Exception as e:
            logger.error("Failed to read %s: %s", pdf, e)
            continue

        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            logger.info("No text in %s", pdf.name)
            processed[str(pdf)] = h
            save_processed(processed)
            continue

        base = excel_map.get(_normalize_fn(pdf.name), {}) if excel_map else {}
        payloads = []
        for i, ch in enumerate(chunks):
            try:
                lang = detect(ch[:5000])
            except Exception:
                lang = "unknown"

            pl = {
                "point_id": deterministic_point_id(pdf.name, h, i),
                "text": ch,
                "source": pdf.name,
                "path": str(pdf.resolve()),
                "chunk_index": i,
                "lang": lang,
            }
            for k, v in base.items():
                if pd.isna(v): 
                    continue
                pl[k] = v
            payloads.append(pl)

        # Embed & upsert in batches
        for i in range(0, len(chunks), BATCH_SIZE):
            seg = chunks[i : i + BATCH_SIZE]
            vecs = embedder.encode(seg, normalize_embeddings=True).tolist()
            upsert_batch(client, vecs, payloads[i : i + BATCH_SIZE])

        processed[str(pdf)] = h
        save_processed(processed)
        total_chunks += len(chunks)
        updated_files += 1
        logger.info("Upserted %d chunks from %s", len(chunks), pdf.name)

    dur = time.time() - t0
    logger.info("✅ Done. Files processed: %d (updated=%d, skipped=%d), Chunks: %d, Time: %.1fs",
                len(pdfs), updated_files, skipped_files, total_chunks, dur)

if __name__ == "__main__":
    main()
