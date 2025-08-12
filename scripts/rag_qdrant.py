"""
Lightweight retrieval helpers for Qdrant + multilingual E5 embeddings.

- Uses Qdrant Query API (`query_points`) with qdrant-client >= 1.9
- Embeddings: intfloat/multilingual-e5-small (great multilingual recall)
- Returns simple `Hit` objects with text, source, score
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

# ---------- Config ----------
ROOT_DIR = Path(__file__).resolve().parents[1]
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "tender_chunks")

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-small")
NORMALIZE_EMBEDDINGS = True

DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# ---------- Logging ----------
logger = logging.getLogger("rag_qdrant")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

# ---------- Singletons ----------
_client: Optional[QdrantClient] = None
_embedder: Optional[SentenceTransformer] = None


def get_qdrant() -> QdrantClient:
    """Create/reuse a Qdrant client."""
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
        logger.info("Qdrant connected: %s", QDRANT_URL)
    return _client


def get_embedder() -> SentenceTransformer:
    """Create/reuse the embedding model."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
        logger.info("Embedding model loaded: %s", EMBED_MODEL_NAME)
    return _embedder


def _encode_query(text: str) -> List[float]:
    """
    Convert a user query to an embedding.
    E5 family: prepend 'query: ' for best retrieval quality.
    """
    txt = f"query: {text}"
    emb = get_embedder().encode([txt], normalize_embeddings=NORMALIZE_EMBEDDINGS)[0]
    return emb.tolist()


@dataclass
class Hit:
    text: str
    source: str
    score: float


def search(query: str, top_k: int = DEFAULT_TOP_K) -> List[Hit]:
    """
    Vector search in Qdrant via Query API. Returns top_k hits sorted by score.
    """
    vec = _encode_query(query)
    client = get_qdrant()

    res = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vec,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
        search_params=models.SearchParams(hnsw_ef=128, exact=False),
    )

    hits: List[Hit] = []
    for p in res.points:
        payload = p.payload or {}
        text = payload.get("text", "")
        source = payload.get("source", "")
        hits.append(Hit(text=text, source=source, score=float(p.score)))
    return hits


def abs_source_path(source: str) -> Path:
    """
    Convert a Qdrant 'source' payload (usually relative path) into an absolute path.
    """
    p = Path(source)
    if not p.is_absolute():
        p = (ROOT_DIR / p).resolve()
    return p