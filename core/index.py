# core/index.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import logging, hashlib
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from .domain import DocumentPage, DocumentChunk
from .io import PDFLoader, ExcelMetadataJoiner
from .config import CFG
from uuid import uuid5, NAMESPACE_URL

class PageAwareChunker:
    def __init__(self, size: int, overlap: int):
        self.size, self.overlap = size, overlap

    def split(self, pages: List[DocumentPage]) -> List[DocumentChunk]:
        text_acc, page_acc, chunks = [], [], []
        idx = 0

        def flush():
            nonlocal idx, text_acc, page_acc
            if not text_acc: return
            text = "".join(text_acc)
            page_start, page_end = page_acc[0], page_acc[-1]
            chunks.append(DocumentChunk(
                chunk_index=idx,
                text=text,
                source_path=pages[0].source_path if pages else None,
                page_start=page_start,
                page_end=page_end,
                meta={}
            ))
            idx += 1
            keep = text[-self.overlap:] if self.overlap > 0 else ""
            text_acc = [keep]
            page_acc = [page_end] if self.overlap > 0 else []

        for p in pages:
            t = p.text or ""
            if not t: 
                continue
            cursor = 0
            while cursor < len(t):
                space_left = self.size - sum(len(x) for x in text_acc)
                if space_left <= 0:
                    flush(); space_left = self.size
                take = t[cursor: cursor + space_left]
                text_acc.append(take)
                if p.page_number not in page_acc:
                    page_acc.append(p.page_number)
                cursor += len(take)
        flush()
        return chunks

class Indexer:
    def __init__(self, cfg=CFG):
        self.cfg = cfg
        self.loader = PDFLoader()
        self.chunker = PageAwareChunker(cfg.chunk_size, cfg.chunk_overlap)
        self.embedder = SentenceTransformer(cfg.embed_model, device="cuda" if self._cuda() else "cpu")
        self.client = QdrantClient(url=cfg.qdrant_url)
        dim = self.embedder.get_sentence_embedding_dimension()
        self._ensure_collection(dim)
        self.joiner = ExcelMetadataJoiner()

    def _cuda(self) -> bool:
        try:
            import torch; return torch.cuda.is_available()
        except Exception:
            return False

    def _ensure_collection(self, dim: int):
        try:
            self.client.get_collection(self.cfg.qdrant_collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.cfg.qdrant_collection,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )

    def _embed(self, texts: list[str]) -> np.ndarray:
        out = self.embedder.encode([f"passage: {t}" for t in texts], normalize_embeddings=True, batch_size=32)
        return np.asarray(out, dtype="float32")

    def _point_id(self, doc_hash: str, chunk_idx: int) -> str:
    # Deterministic UUID based on doc hash + chunk index
        return str(uuid5(NAMESPACE_URL, f"{doc_hash}|{chunk_idx}"))

    def build(self, extract_dir: Path | None = None, metadata_path: Path | None = None):
        base = Path(extract_dir or self.cfg.extract_dir)
        pdfs = sorted(base.rglob("*.pdf"))
        logging.info(f"Found {len(pdfs)} PDFs")
        for pdf in pdfs:
            pages = self.loader.load_pages(pdf)
            chunks: List[DocumentChunk] = self.chunker.split(pages)
            if not chunks:
                logging.info(f"Skipped (no text): {pdf}")
                continue

            # Deterministic per-file hash
            try:
                h = hashlib.sha1(pdf.read_bytes()).hexdigest()
            except Exception:
                # fallback: use path if read_bytes not allowed
                h = hashlib.sha1(str(pdf).encode("utf-8")).hexdigest()

            payloads, texts = [], []
            for c in chunks:
                meta = self.joiner.enrich(c.source_path, {**c.meta})
                pl = {**c.payload(), **meta, "doc_hash": h}
                payloads.append(pl)
                texts.append(c.text)

            vecs = self._embed(texts)
            points = [
                models.PointStruct(
                    id=self._point_id(pl["doc_hash"], pl["chunk_idx"]),  # <- NOT None
                    vector=v.tolist(),
                    payload=pl,
                )
                for v, pl in zip(vecs, payloads)
            ]
            self.client.upsert(collection_name=self.cfg.qdrant_collection, points=points)
            logging.info(f"Upserted {len(points)} chunks from {pdf}")
