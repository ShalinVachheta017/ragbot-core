from __future__ import annotations

import logging, os, re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

# --- Config ---
ROOT_DIR = Path(__file__).resolve().parents[1]
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "tender_docs")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-small")
NORMALIZE_EMBEDDINGS = True
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "4"))       # stricter default
DEFAULT_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.45"))

logger = logging.getLogger("rag_qdrant")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

_client: Optional[QdrantClient] = None
_embedder: Optional[SentenceTransformer] = None

# Detect 8-digit DTAD IDs in query
DTAD_RE = re.compile(r"\b(\d{8})\b")


def get_qdrant() -> QdrantClient:
    """Return a cached Qdrant client."""
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
        logger.info("Qdrant connected: %s", QDRANT_URL)
    return _client


def get_embedder() -> SentenceTransformer:
    """Return a cached embedding model."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
        logger.info("Embedding model loaded: %s", EMBED_MODEL_NAME)
    return _embedder


def _encode_query(text: str) -> List[float]:
    """Encode query with E5 (requires 'query:' prefix)."""
    vec = get_embedder().encode([f"query: {text}"], normalize_embeddings=NORMALIZE_EMBEDDINGS)[0]
    return vec.tolist()


@dataclass
class Hit:
    pid: str
    source: str
    page: Optional[int]
    score: float
    text: str


def search(query: str, top_k: int = DEFAULT_TOP_K, min_score: float = DEFAULT_MIN_SCORE) -> List[Hit]:
    """
    Search Qdrant with stricter DTAD-ID handling.
    If a DTAD-ID is in query → FORCE filter only that id.
    Otherwise → semantic search.
    """
    client = get_qdrant()

    # --- Case 1: DTAD-ID strict filter ---
    m = DTAD_RE.search(query)
    if m:
        dtad_id = int(m.group(1))
        qfilter = models.Filter(must=[
            models.FieldCondition(
                key="dtad_id",
                match=models.MatchValue(value=dtad_id)
            )
        ])
        logger.info(f"Strict search enforced for DTAD-ID={dtad_id}")

        res = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=_encode_query(query),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
            query_filter=qfilter,
        )
    else:
        # --- Case 2: normal semantic search ---
        res = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=_encode_query(query),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
        )

    # --- Collect results ---
    hits: List[Hit] = []
    for i, p in enumerate(res, start=1):
        payload = (p.payload or {})
        s = float(getattr(p, "score", 1.0))
        if s < min_score:
            continue
        hit = Hit(
            pid=str(p.id),
            source=payload.get("source", ""),
            page=payload.get("page"),
            score=s,
            text=payload.get("text", ""),
        )
        hits.append(hit)

        logger.info(
            f"Hit {i}: score={hit.score:.3f}, "
            f"dtad_id={payload.get('dtad_id')}, "
            f"source={hit.source}, page={hit.page}, "
            f"text={hit.text[:120]}..."
        )

    if m and not hits:
        logger.warning(f"No results found for DTAD-ID {m.group(1)}")
    return hits


def abs_source_path(source: str) -> Path:
    """Resolve relative source path to absolute path under project root."""
    p = Path(source)
    if not p.is_absolute():
        p = (ROOT_DIR / p).resolve()
    return p


if __name__ == "__main__":
    test_query = "Wann ist das Submission-Datum für DTAD-ID 2004749?"
    results = search(test_query, top_k=4)
    for r in results:
        print(r)
