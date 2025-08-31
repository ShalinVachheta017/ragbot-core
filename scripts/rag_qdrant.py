# rag_qdrant.py
from __future__ import annotations

import logging, os, re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

# --- Config (env with sane defaults) ---
ROOT_DIR = Path(__file__).resolve().parents[1]
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "tender_docs")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-small")
NORMALIZE_EMBEDDINGS = True
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "8"))

logger = logging.getLogger("rag_qdrant")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

_client: Optional[QdrantClient] = None
_embedder: Optional[SentenceTransformer] = None

# Detect 8-digit DTAD IDs in the query
DTAD_RE = re.compile(r"\b(\d{8})\b")


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
        logger.info("Qdrant connected: %s", QDRANT_URL)
    return _client


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
        logger.info("Embedding model loaded: %s", EMBED_MODEL_NAME)
    return _embedder


def _encode_query(text: str) -> List[float]:
    # E5 requires 'query: ' prefix for queries
    vec = get_embedder().encode([f"query: {text}"], normalize_embeddings=NORMALIZE_EMBEDDINGS)[0]
    return vec.tolist()


@dataclass
class Hit:
    pid: str
    source: str
    page: Optional[int]
    score: float
    text: str


def search(query: str, top_k: int = DEFAULT_TOP_K, min_score: float | None = 0.25) -> List[Hit]:
    """
    Legacy-client compatible search:
    - uses client.search(..., query_vector=..., query_filter=...)
    - returns a list of Hit, filtered by optional min_score
    """
    vec = _encode_query(query)
    client = get_qdrant()

    # Build payload filter if a DTAD ID is present
    qfilter = None
    m = DTAD_RE.search(query)
    if m:
        # If your payload stored dtad_id as string, use value=m.group(1)
        qfilter = models.Filter(must=[
            models.FieldCondition(
                key="dtad_id",
                match=models.MatchValue(value=int(m.group(1)))
            )
        ])  # Payload filtering is the right way to target a specific tender.  # noqa

    # NOTE: client.search returns a LIST of ScoredPoint on legacy clients
    res = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=vec,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
        search_params=models.SearchParams(hnsw_ef=128, exact=False),
        query_filter=qfilter,
    )

    hits: List[Hit] = []
    for p in res:  # <-- iterate the list (NOT res.points)
        payload = (p.payload or {})
        s = float(p.score)
        if (min_score is not None) and (s < min_score):
            continue
        hits.append(Hit(
            pid=str(p.id),
            source=payload.get("source", ""),
            page=payload.get("page"),
            score=s,
            text=payload.get("text", ""),
        ))
    return hits


def abs_source_path(source: str) -> Path:
    p = Path(source)
    if not p.is_absolute():
        p = (ROOT_DIR / p).resolve()
    return p
