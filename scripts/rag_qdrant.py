# scripts/rag_qdrant.py
"""
RAG helper for Qdrant:
- Connects to Qdrant and runs vector search with optional filters
- Optional CrossEncoder reranking (robust to meta-tensor init)
- Exported API: search(...), info(), Hit dataclass
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    VectorParams,
)

# ----------------- Logging -----------------
logger = logging.getLogger("rag_qdrant")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ----------------- Config (env overrides) -----------------
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # optional
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "tender_docs")

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-small")
EMBED_DEVICE = os.getenv("EMBED_DEVICE", "cpu")  # "cpu" or "cuda"

RERANK_MODEL_NAME = os.getenv("RERANK_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANK_DEVICE = os.getenv("RERANK_DEVICE", "cpu")  # "cpu" or "cuda"
RERANK_ENABLED_DEFAULT = True  # app can still pass rerank=False

# ----------------- Singletons -----------------
_client: Optional[QdrantClient] = None
_embedder: Optional[SentenceTransformer] = None
_reranker: Optional[CrossEncoder] = None


# ----------------- Public types -----------------
@dataclass
class Hit:
    text: str
    source: str
    score: float
    payload: Dict[str, Any]


# ----------------- Helpers: clients/models -----------------
def get_qdrant() -> QdrantClient:
    global _client
    if _client is not None:
        return _client
    _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _client


def ensure_collection(dim: int) -> None:
    """
    Create collection if missing; do nothing if it exists.
    """
    client = get_qdrant()
    try:
        # qdrant-client >=1.7.0
        exists = client.collection_exists(QDRANT_COLLECTION)
    except Exception:
        # Fallback trick for older clients
        try:
            client.get_collection(QDRANT_COLLECTION)
            exists = True
        except Exception:
            exists = False
    if not exists:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info("Created collection %s (dim=%s)", QDRANT_COLLECTION, dim)


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is not None:
        return _embedder
    logger.info("Loading embedder: %s on %s", EMBED_MODEL_NAME, EMBED_DEVICE)
    _embedder = SentenceTransformer(EMBED_MODEL_NAME, device=EMBED_DEVICE)
    return _embedder


def get_reranker():
    """
    Load CrossEncoder robustly. Avoid meta-device init pitfalls by disabling
    low_cpu_mem_usage / device_map and respecting RERANK_DEVICE. Falls back
    to a small CPU model or a no-op scorer on failure.
    """
    global _reranker
    if _reranker is not None:
        return _reranker

    automodel_args = {
        "low_cpu_mem_usage": False,   # avoid accelerate 'meta' init
        "device_map": None,
        "torch_dtype": torch.float32,
    }

    name = RERANK_MODEL_NAME
    device = RERANK_DEVICE

    try:
        logger.info("Loading reranker: %s on %s", name, device)
        _reranker = CrossEncoder(
            name,
            device=device,
            trust_remote_code=True,
            automodel_args=automodel_args,
        )
        return _reranker
    except NotImplementedError as e:
        logger.warning("Reranker meta-tensor issue (%s). Falling back to MiniLM on CPU.", e)
        name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        device = "cpu"
        _reranker = CrossEncoder(
            name,
            device=device,
            trust_remote_code=True,
            automodel_args=automodel_args,
        )
        return _reranker
    except Exception as e:
        logger.error("Failed to load reranker (%s). Using no-op scorer.", e)

        class _Noop:
            def predict(self, pairs: List[Tuple[str, str]]):
                return np.zeros(len(pairs))

        _reranker = _Noop()
        return _reranker


# ----------------- Core: search -----------------
def _build_filter(filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
    """
    Server-side filters supported:
      - lang: exact match (e.g., "de")
      - cpv:  exact match (string)
    """
    if not filters:
        return None
    must = []
    if "lang" in filters and filters["lang"]:
        must.append(FieldCondition(key="lang", match=MatchValue(value=str(filters["lang"]))))
    if "cpv" in filters and filters["cpv"]:
        must.append(FieldCondition(key="cpv", match=MatchValue(value=str(filters["cpv"]))))
    return Filter(must=must) if must else None


def _embed_query(text: str) -> List[float]:
    # IMPORTANT: we embedded passages as raw text (no "passage:" prefix),
    # so keep the query raw as well (no "query:" prefix) to avoid a mismatch.
    emb = get_embedder().encode([text], normalize_embeddings=True)[0]
    return emb.tolist() if hasattr(emb, "tolist") else list(emb)


def _rerank(query: str, points: List[Any], top_k: int) -> List[Any]:
    if not points:
        return []
    pairs = [(query, p.payload.get("text", "")) for p in points]
    scores = get_reranker().predict(pairs).tolist()
    # Attach and sort by reranker score (desc)
    enriched = [(float(s), p) for s, p in zip(scores, points)]
    enriched.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in enriched[:top_k]]


def search(
    query: str,
    top_k: int = 5,
    initial_top_k: int = 50,
    filters: Optional[Dict[str, Any]] = None,
    rerank: bool = RERANK_ENABLED_DEFAULT,
) -> List[Hit]:
    """
    Vector search (Qdrant) + optional CrossEncoder rerank.
    Returns Hit list with text, source, score (similarity or rerank score), payload.
    """
    if not query or not query.strip():
        return []

    qvec = _embed_query(query)
    client = get_qdrant()

    # Ensure collection exists with correct dim (safe no-op if present)
    try:
        dim = get_embedder().get_sentence_embedding_dimension()
        ensure_collection(dim)
    except Exception:
        pass

    qfilter = _build_filter(filters)

    # Initial vector search (large K for later rerank)
    # Use client.search -> returns List[ScoredPoint]
    points = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=qvec,
        limit=max(top_k, initial_top_k),
        query_filter=qfilter,
        with_payload=True,
        score_threshold=None,  # allow all; we'll gate by K
    )

    if not points:
        return []

    final_points = _rerank(query, points, top_k=top_k) if rerank else points[:top_k]

    hits: List[Hit] = []
    for p in final_points:
        payload = dict(p.payload or {})
        txt = payload.get("text", "")
        src = payload.get("source", payload.get("path", str(p.id)))
        # Choose score: use rerank score if we computed it, else qdrant similarity
        sc = float(getattr(p, "score", 0.0))
        hits.append(Hit(text=txt, source=str(src), score=sc, payload=payload))
    return hits


# ----------------- Utility for the UI -----------------
def info() -> Dict[str, Any]:
    return {
        "qdrant_url": QDRANT_URL,
        "collection": QDRANT_COLLECTION,
        "embed_model": EMBED_MODEL_NAME,
        "rerank_model": RERANK_MODEL_NAME,
    }


# ----------------- CLI smoke test -----------------
if __name__ == "__main__":
    logger.info("Backend info: %s", info())
    res = search("Vergabe DE test", top_k=3, initial_top_k=50, filters={"lang": "de"}, rerank=True)
    for i, h in enumerate(res, 1):
        logger.info("[%d] score=%.3f src=%s len=%d", i, h.score, h.source, len(h.text))
