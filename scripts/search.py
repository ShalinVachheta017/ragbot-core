# core/search.py
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

from .config import CFG

# Keep embedder behavior stable if HF repo updates
PINNED_SHA = "f1944de8402dcd5f2b03f822a4bc22a7f2de2eb9"


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    # prefer_grpc=False for widest compatibility on Windows
    return QdrantClient(url=CFG.qdrant_url, prefer_grpc=False, timeout=60.0)


@lru_cache(maxsize=1)
def _embedder() -> SentenceTransformer:
    # trust_remote_code is needed for Jina v3; revision keeps it stable
    device = "cuda"
    try:
        import torch  # local import to avoid hard dep
        if not torch.cuda.is_available():
            device = "cpu"
    except Exception:
        device = "cpu"

    return SentenceTransformer(
        CFG.embed_model,
        trust_remote_code=True,
        revision=PINNED_SHA,
        device=device,
    )


@lru_cache(maxsize=1)
def _collection_cfg() -> Tuple[str, Optional[Dict[str, int]] | int | None]:
    """
    Returns:
      ("missing", None)  if collection not found
      ("single", size)   for single-vector collections
      ("named", {name: size, ...}) for named vectors
    """
    try:
        info = _client().get_collection(CFG.qdrant_collection)
    except Exception:
        return ("missing", None)

    vecs = info.config.params.vectors
    if hasattr(vecs, "size"):
        return ("single", int(vecs.size))
    # named vectors
    return ("named", {str(k): int(v.size) for k, v in vecs.items()})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _qdrant_dim() -> Optional[int]:
    kind, data = _collection_cfg()
    if kind == "missing":
        return None
    if kind == "single":
        return int(data)  # type: ignore[arg-type]
    # named: pick a conventional name if present, else first size
    sizes: Dict[str, int] = data  # type: ignore[assignment]
    if "text" in sizes:
        return sizes["text"]
    return next(iter(sizes.values())) if sizes else None


def _select_vector_name() -> Optional[str]:
    kind, data = _collection_cfg()
    if kind in ("missing", "single"):
        return None
    sizes: Dict[str, int] = data  # type: ignore[assignment]
    return "text" if "text" in sizes else next(iter(sizes.keys()))


def _effective_model_dim() -> int:
    try:
        return int(_embedder().get_sentence_embedding_dimension())
    except Exception:
        # very defensive fallback
        v = _embedder().encode(["probe"], normalize_embeddings=True)
        return int(v.shape[-1])


def _ensure_dims_ok() -> None:
    qdim = _qdrant_dim()
    if qdim is None:
        raise RuntimeError(
            f"Qdrant collection '{CFG.qdrant_collection}' not found at {CFG.qdrant_url}."
        )
    model_dim = _effective_model_dim()
    # We'll slice down to qdrant dim if model is larger; if model is smaller, error.
    if model_dim < qdim:
        raise RuntimeError(
            f"Embedding dim mismatch: model={model_dim} < qdrant={qdim}. "
            "Recreate the collection with the model's size or switch model."
        )


def _vector_arg(vec: Sequence[float]):
    """
    Build the 'query_vector' argument for Qdrant .search(), supporting single and named vectors.
    """
    name = _select_vector_name()
    return vec if name is None else (name, vec)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_query(text: str) -> List[float]:
    """
    Encode a user query with the Jina v3 query prefix and return a float list.
    Auto-slices to the collection's vector size if needed.
    """
    prefix = getattr(CFG, "embed_query_prefix", "search_query: ")
    embs = _embedder().encode(
        [prefix + text],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    v: np.ndarray = embs[0].astype("float32", copy=False)

    qdim = _qdrant_dim()
    if qdim is not None and v.shape[0] > qdim:
        v = v[:qdim]
    return v.tolist()


def search_dense(query_text: str, limit: Optional[int] = None, min_score: Optional[float] = None):
    """
    Dense vector search against the configured collection.
    Returns: list[qdrant_client.models.ScoredPoint].
    """
    _ensure_dims_ok()
    limit = int(limit or getattr(CFG, "topk_candidate", 100))
    qv = embed_query(query_text)

    params = qmodels.SearchParams(
        hnsw_ef=int(getattr(CFG, "hnsw_ef_search", 128))
    )

    res = _client().search(
        collection_name=CFG.qdrant_collection,
        query_vector=_vector_arg(qv),
        limit=limit,
        with_payload=True,
        with_vectors=False,
        params=params,
        score_threshold=None,  # post-filter below
    )

    # Optional post-filter by score
    thresh = float(getattr(CFG, "min_score", 0.0)) if min_score is None else float(min_score)
    if thresh > 0:
        res = [r for r in res if (r.score is not None and float(r.score) >= thresh)]
    return res


def rrf(result_sets: List[Sequence], k: int = 60):
    """
    Reciprocal Rank Fusion over multiple result lists.
    Each item must have `.id`. Returns a fused, re-ranked list.
    """
    scores: dict[str, float] = {}
    keep: dict[str, object] = {}
    for results in result_sets:
        for rank, r in enumerate(results, start=1):
            pid = str(r.id)
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank)
            keep.setdefault(pid, r)
    return sorted(keep.values(), key=lambda r: scores[str(r.id)], reverse=True)


def count_points() -> Optional[int]:
    """
    Count points in the configured collection.
    Returns None if the collection does not exist or cannot be read.
    """
    try:
        # quick existence check
        kind, _ = _collection_cfg()
        if kind == "missing":
            return None
        return _client().count(CFG.qdrant_collection, exact=True).count
    except Exception:
        return None


def is_alive() -> bool:
    try:
        return bool(_client().is_alive())
    except Exception:
        return False
