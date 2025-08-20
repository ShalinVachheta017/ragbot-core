# scripts/tools/ensure_qdrant.py
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from uuid import uuid4

QDRANT_URL       = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME  = os.getenv("QDRANT_COLLECTION", "tender_docs")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-small")

embedder = SentenceTransformer(EMBED_MODEL_NAME)
dim = embedder.get_sentence_embedding_dimension()
client = QdrantClient(url=QDRANT_URL)

def ensure_collection():
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

def seed():
    texts = [
        "VergabeNerd ist ein lokales RAG-System für deutsche Ausschreibungen.",
        "The system supports bilingual Q&A (DE/EN)."
    ]
    vecs = embedder.encode(texts, normalize_embeddings=True).tolist()
    pts = [PointStruct(id=str(uuid4()), vector=v, payload={"source":"seed"}) for v in vecs]
    client.upsert(collection_name=COLLECTION_NAME, points=pts)

if __name__ == "__main__":
    ensure_collection()
    # Optional: seed a couple of points so search won't return empty
    seed()
    info = client.get_collection(COLLECTION_NAME)
    print(f"✅ Collection ready: {COLLECTION_NAME} (dim={dim})")
