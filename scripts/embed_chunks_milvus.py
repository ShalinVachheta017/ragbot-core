import os
import hashlib
import logging
from pathlib import Path
from tqdm import tqdm
import torch
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
from config import EXTRACT_DIR, EMBED_MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP, BATCH_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embed_chunks_milvus")

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_and_chunk(path: Path):
    loader = PyMuPDFLoader(str(path))
    docs = loader.load()
    for d in docs:
        d.metadata.update({"source": str(path), "hash": file_hash(path)})
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter.split_documents(docs)

def main():
    pdfs = list(Path(EXTRACT_DIR).rglob("*.pdf"))
    logger.info(f"Found {len(pdfs)} PDFs")
    if not pdfs:
        return

    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME,
                                      model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"})

    all_chunks = []
    for pdf in tqdm(pdfs, desc="📄 Chunking"):
        try:
            chunks = load_and_chunk(pdf)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.warning(f"❌ {pdf.name}: {e}")

    logger.info(f"🧩 Total chunks: {len(all_chunks)}")
    texts = [c.page_content for c in all_chunks]
    metadatas = [c.metadata for c in all_chunks]

    Milvus.from_texts(
        texts=texts,
        embedding=embedding,
        metadatas=metadatas,
        connection_args={
            "host": "localhost",
            "port": "19530"
        },
        collection_name="tender_docs",
    )
    logger.info("✅ Embedding stored in Milvus.")

if __name__ == "__main__":
    main()