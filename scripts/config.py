from pathlib import Path
import os

# === Folder Paths ===
ROOT_DIR = Path(__file__).resolve().parent.parent
EXTRACT_DIR = ROOT_DIR / "extractdirect"
METADATA_DIR = ROOT_DIR / "metadata"
LOG_DIR = ROOT_DIR / "logs"
CHROMA_DB_DIR = ROOT_DIR / "chroma_db"  # unused now, kept for compatibility

# === File Paths ===
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CLEANED_EXCEL = METADATA_DIR / "cleaned_metadata.xlsx"
EMBED_LOG_FILE = LOG_DIR / "embed_chunks.log"

# === Embedding Config ===
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-small")
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "400"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))

# === Vector DB Settings ===
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "tender_docs")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")

# === Ollama / LLM Settings ===
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
