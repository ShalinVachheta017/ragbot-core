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

    # If you ever change the filename, the UI/parse step will stay in sync via this:
    metadata_filename: str = "cleaned_metadata.xlsx"

    # ─── Models / Vector DB ────────────────────────────────────────────────
    llm_model:         str  = "qwen2.5:1.5b"
    qdrant_url: str = "http://localhost:6333" # health check URL


    # Embeddings (Jina v3 = 1024-D)
    embed_model:       str  = "jinaai/jina-embeddings-v3"
    embed_dim:         int  = 1024

    # ✅ Jina v3 requires different prefixes for docs vs. queries
    embed_doc_prefix:  str  = "search_document: "
    embed_query_prefix:str  = "search_query: "

    qdrant_collection: str  = "tender_docs_jina-v3_d1024_fresh"

    # ─── Embedding-time knobs ──────────────────────────────────────────────
    embed_batch_size:   int = 32
    max_seq_length:     int = 8192
    embed_flush_chunks: int = 1000

    # ─── Chunking ──────────────────────────────────────────────────────────
    chunk_size:    int = 1000
    chunk_overlap: int = 400

    # ─── Retrieval ────────────────────────────────────────────────────────
    # Keep your existing knobs for compatibility…
    topk_candidate: int   = 100
    final_k:        int   = 16
    min_score:      float = 0.1
    hnsw_ef_search: int   = 128
    use_hybrid:     bool  = True

    # …and add language routing toggles used by the new retriever
    # Option B: force all retrieval through a German query (EN→DE translation first)
    force_german_retrieval: bool = False
    # Option C: run both (original + German) and fuse with RRF
    dual_query: bool = True

    # ─── Re-ranker (BGE-m3) ───────────────────────────────────────────────
    use_rerank:        bool   = True
    reranker_model:    str    = "BAAI/bge-reranker-v2-m3"
    rerank_keep:       int    = 24
    rerank_weight:     float  = 0.8
    rerank_batch_size: int    = 64

    # ─── Convenience properties (don’t override via env) ──────────────────
    @property
    def metadata_path(self) -> Path:
        """Full path to the cleaned metadata Excel used by the UI."""
        return self.metadata_dir / self.metadata_filename

    @property
    def top_k(self) -> int:
        """Unified Top-K accessor (maps to your final_k)."""
        return self.final_k


CFG = AppConfig()
