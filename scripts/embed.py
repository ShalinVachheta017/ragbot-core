from core.index import Indexer

if __name__ == "__main__":
    Indexer().build()
    print("✅ Index build complete (Qdrant upserted).")
