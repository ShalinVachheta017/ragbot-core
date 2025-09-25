# core/config.py
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAGBOT_", case_sensitive=False)

    # ─── Paths ─────────────────────────────────────────────────────────────
    raw_dir:      Path = ROOT / "data" / "raw"
    extract_dir:  Path = ROOT / "data" / "extract"
    metadata_dir: Path = ROOT / "data" / "metadata"
    logs_dir:     Path = ROOT / "data" / "logs"
    state_dir:    Path = ROOT / "data" / "state"

    # ─── Models / Vector DB ────────────────────────────────────────────────
    llm_model:         str  = "qwen2.5:1.5b"
    qdrant_url:        str  = "http://127.0.0.1:6333"
    embed_model:       str  = "jinaai/jina-embeddings-v3"
    embed_dim:         int  = 1024
    embed_doc_prefix:  str  = "" # Add this line
    qdrant_collection: str = "tender_docs_jina-v3_d1024_fresh"

    # ─── Embedding-time knobs ──────────────────────────────────────────────
    embed_batch_size:   int = 32
    max_seq_length:     int = 8192
    embed_flush_chunks: int = 1000

    # ─── Chunking ──────────────────────────────────────────────────────────
    chunk_size:    int = 1000
    chunk_overlap: int = 400

    # ─── Retrieval ────────────────────────────────────────────────────────
    topk_candidate: int   = 100
    final_k:        int   = 16
    min_score:      float = 0.1
    hnsw_ef_search: int   = 128
    use_hybrid:     bool  = True

    # ─── Re-ranker (BGE-m3) ───────────────────────────────────────────────
    use_rerank:      bool   = True
    reranker_model:  str    = "BAAI/bge-reranker-v2-m3"
    rerank_keep:     int    = 24
    rerank_weight:   float  = 0.8
    rerank_batch_size:int   = 64


CFG = AppConfig()