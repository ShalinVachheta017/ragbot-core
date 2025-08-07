from pathlib import Path

# === Folder Paths ===
ROOT_DIR = Path(__file__).resolve().parent.parent
EXTRACT_DIR = ROOT_DIR / "extractdirect"
METADATA_DIR = ROOT_DIR / "metadata"
LOG_DIR = ROOT_DIR / "logs"
CHROMA_DB_DIR = ROOT_DIR / "chroma_db"

# === File Paths ===
CLEANED_EXCEL = METADATA_DIR / "cleaned_metadata.xlsx"
EMBED_LOG_FILE = LOG_DIR / "embed_chunks.log"

# === Embedding Config ===
EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 400
BATCH_SIZE = 32

# === LangChain Settings ===
COLLECTION_NAME = "tender_docs"

# === Ollama / LLM Settings ===
OLLAMA_MODEL = "qwen2.5"
OLLAMA_API_BASE_URL = "http://localhost:11434/api/chat/completions"
