from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

client = QdrantClient(url="http://127.0.0.1:6333")
model = SentenceTransformer("intfloat/multilingual-e5-small")

q = "construction contract draft"
vec = model.encode(f"query: {q}", normalize_embeddings=True).tolist()

res = client.query_points(
    collection_name="tender_chunks",
    query=vec,
    with_payload=True,
    limit=5
)

for p in res.points:
    print(round(p.score, 4), p.payload.get("source"))
