# core/config.py
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict  # <-- NEW

ROOT = Path(__file__).resolve().parents[1]

class AppConfig(BaseSettings):
    # env overrides like RAGBOT_QDRANT_URL=http://127.0.0.1:6333
    model_config = SettingsConfigDict(env_prefix="RAGBOT_", case_sensitive=False)

    # Paths
    raw_dir: Path = ROOT / "data" / "raw"
    extract_dir: Path = ROOT / "data" / "extract"
    metadata_dir: Path = ROOT / "data" / "metadata"
    logs_dir: Path = ROOT / "data" / "logs"
    state_dir: Path = ROOT / "data" / "state"

    # Models / DB
    embed_model: str = "intfloat/multilingual-e5-large"
# core/config.py
    llm_model = "qwen2.5:1.5b"
    qdrant_url = "http://127.0.0.1:6333"
    qdrant_collection: str = "tender_docs_m-e5-large_v1"

    # Chunking / Retrieval
    chunk_size: int = 1400
    chunk_overlap: int = 180
    topk_candidate: int = 20
    final_k: int = 8
    min_score: float = 0.25
    hnsw_ef_search: int = 64
    use_hybrid: bool = True
    use_rerank: bool = False

CFG = AppConfig()
