# """
# VergabeNerd LangChain Embedder - FINAL VERSION (Multilingual GPU)
# ✅ Recursively loads PDFs from extractdirect/
# ✅ Uses HuggingFace Embeddings (multilingual-e5-small)
# ✅ Stores embeddings in ChromaDB
# ✅ Logs everything to embed_chunks.log
# """

# import time
# import hashlib
# import logging
# from pathlib import Path
# from tqdm import tqdm
# import torch

# from langchain_community.document_loaders import PyMuPDFLoader
# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain.text_splitter import RecursiveCharacterTextSplitter

# # === Config
# EXTRACT_DIR = Path("extractdirect")
# LOG_FILE = Path("logs/embed_chunks.log")
# CHROMA_DIR = Path("chroma_db")
# EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"
# CHUNK_SIZE = 512
# CHUNK_OVERLAP = 60

# # === Logger Setup
# def setup_logger():
#     logger = logging.getLogger("embed_chunks")
#     logger.setLevel(logging.INFO)
#     formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
#     LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

#     fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
#     fh.setFormatter(formatter)
#     ch = logging.StreamHandler()
#     ch.setFormatter(formatter)

#     logger.addHandler(fh)
#     logger.addHandler(ch)
#     return logger

# logger = setup_logger()

# # === SHA256 Hash
# def file_hash(path):
#     h = hashlib.sha256()
#     with open(path, "rb") as f:
#         for chunk in iter(lambda: f.read(8192), b""):
#             h.update(chunk)
#     return h.hexdigest()

# # === Embedding
# def embed_pdfs(pdf_paths):
#     logger.info(f"🔍 Found {len(pdf_paths)} PDF files")

#     if not pdf_paths:
#         logger.warning("⚠️ No PDFs found. Aborting embedding.")
#         return

#     # Load model
#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     logger.info(f"🧠 Using device: {device.upper()}")

#     embedding = HuggingFaceEmbeddings(
#         model_name=EMBED_MODEL_NAME,
#         model_kwargs={"device": device}
#     )

#     # Splitter
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=CHUNK_SIZE,
#         chunk_overlap=CHUNK_OVERLAP
#     )

#     # Prepare docs
#     all_docs = []
#     for path in tqdm(pdf_paths, desc="📄 Chunking PDFs"):
#         try:
#             loader = PyMuPDFLoader(str(path))
#             docs = loader.load()
#             for doc in docs:
#                 doc.metadata.update({
#                     "source": str(path),
#                     "hash": file_hash(path)
#                 })
#             chunks = splitter.split_documents(docs)
#             all_docs.extend(chunks)
#         except Exception as e:
#             logger.warning(f"❌ Failed to process {path.name}: {e}")

#     logger.info(f"🧩 Total chunks: {len(all_docs)}")

#     # Store in Chroma
#     db = Chroma.from_documents(
#         all_docs,
#         embedding=embedding,
#         persist_directory=str(CHROMA_DIR)
#     )
#     logger.info("✅ Embedding complete. Saved to ChromaDB.")

# # === Main
# def main():
#     logger.info("🚀 Starting PDF embedding...")
#     logger.info(f"📂 Scanning: {EXTRACT_DIR.resolve()}")

#     if not EXTRACT_DIR.exists():
#         logger.error(f"❌ extractdirect folder not found at {EXTRACT_DIR.resolve()}")
#         return

#     pdf_paths = list(EXTRACT_DIR.rglob("*.pdf"))
#     embed_pdfs(pdf_paths)

# if __name__ == "__main__":
#     main()


import os
import time
import hashlib
import logging
from pathlib import Path
from multiprocessing import Pool, cpu_count, Queue, Process
from datetime import datetime
from typing import List
import torch
from tqdm import tqdm
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from config import EXTRACT_DIR, CHROMA_DB_DIR, EMBED_LOG_FILE, EMBED_MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP, BATCH_SIZE

# Setup logger
def setup_logger():
    logger = logging.getLogger("embed_chunks")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    fh = logging.FileHandler(EMBED_LOG_FILE, encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = setup_logger()

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def process_pdf(path: Path):
    loader = PyMuPDFLoader(str(path))
    docs = loader.load()
    for d in docs:
        d.metadata.update({"source": str(path), "hash": file_hash(path)})
    chunks = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP).split_documents(docs)
    return chunks

def embed_and_store(chunks: List, embedding_model, persist_dir: str):
    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    embeddings = embedding_model.embed_documents(texts)
    db = Chroma.from_documents(chunks, embedding=embedding_model, persist_directory=persist_dir)
    logger.info(f"Stored {len(chunks)} chunks to ChromaDB at {persist_dir}")

def main():
    logger.info("Starting batch PDF embedding...")
    pdf_paths = list(Path(EXTRACT_DIR).rglob("*.pdf"))
    logger.info(f"Found {len(pdf_paths)} PDFs in {EXTRACT_DIR}.")
    if not pdf_paths:
        return

    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME,
                                      model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"})
    logger.info(f"Using embedding model: {EMBED_MODEL_NAME}")

    all_chunks = []
    for path in tqdm(pdf_paths, desc="Chunking PDFs"):
        try:
            all_chunks.extend(process_pdf(path))
        except Exception as e:
            logger.warning(f"Failed to chunk {path.name}: {e}")

    logger.info(f"Total chunks created: {len(all_chunks)}")

    # Deduplication by metadata hash
    unique = {}
    for ch in all_chunks:
        h = hashlib.sha256(ch.page_content.encode('utf-8')).hexdigest()
        if h not in unique:
            unique[h] = ch
    chunks = list(unique.values())
    logger.info(f"{len(chunks)} chunks after deduplication")

    # Batch embedding
    batch_size = BATCH_SIZE
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1} with {len(batch)} chunks")
        embed_and_store(batch, embedding, str(CHROMA_DB_DIR))

    logger.info("Batch embedding complete.")

if __name__ == "__main__":
    main()
