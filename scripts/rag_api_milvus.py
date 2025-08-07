import os
import logging
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
from langdetect import detect
from config import EMBED_MODEL_NAME, OLLAMA_MODEL, OLLAMA_API_BASE_URL

app = FastAPI(title="RAG API (Milvus)", description="FastAPI RAG backend using Milvus")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_api")

device = "cuda" if __import__('torch').cuda.is_available() else "cpu"
embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME, model_kwargs={"device": device})

db = Milvus(
    embedding_function=embedding,
    connection_args={"host": "localhost", "port": "19530"},
    collection_name="tender_docs"
)

def ollama_query(prompt: str):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "Answer using the given context."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
    }
    r = requests.post(OLLAMA_API_BASE_URL, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

@app.post("/v1/chat/completions")
async def complete(req: Request):
    try:
        data = await req.json()
        messages = data.get("messages", [])
        user_msg = "
".join([m["content"] for m in messages if m["role"] == "user"])
        lang = detect(user_msg)
        docs = db.similarity_search(user_msg, k=5)
        ctx = "

".join(d.page_content for d in docs)
        full_prompt = f"Context:
{ctx}

Question:
{user_msg}"
        answer = ollama_query(full_prompt)
        return JSONResponse({
            "model": OLLAMA_MODEL,
            "language": lang,
            "answer": answer,
            "matched_documents": [
                {"source": d.metadata.get("source"), "excerpt": d.page_content[:300]} for d in docs
            ]
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        return PlainTextResponse(str(e), status_code=500)

@app.get("/health")
def health():
    return {"status": "ok"}