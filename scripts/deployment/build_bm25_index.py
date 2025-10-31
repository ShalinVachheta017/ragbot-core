"""
Build BM25 index from Qdrant collection for hybrid search.

This script:
1. Fetches all documents from Qdrant
2. Builds a BM25 index for keyword search
3. Saves the index to disk

Run this after embedding documents into Qdrant.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient
from core.config import CFG
from core.hybrid_search import BM25Index


def fetch_all_documents() -> list[dict]:
    """
    Fetch all documents from Qdrant collection.
    
    Returns:
        List of dicts with 'id', 'text', and 'metadata' keys
    """
    print(f"📡 Connecting to Qdrant at {CFG.qdrant_url}...")
    client = QdrantClient(url=CFG.qdrant_url, prefer_grpc=False, timeout=60)
    
    # Check if collection exists
    if not client.collection_exists(CFG.qdrant_collection):
        print(f"❌ Collection '{CFG.qdrant_collection}' does not exist!")
        print("\nPlease run the embedding pipeline first:")
        print("  python scripts/embed.py")
        sys.exit(1)
    
    # Get collection info
    collection_info = client.get_collection(CFG.qdrant_collection)
    total_docs = collection_info.points_count
    print(f"📊 Found {total_docs} documents in collection '{CFG.qdrant_collection}'")
    
    # Scroll through all documents
    print("📥 Fetching documents...")
    documents = []
    offset = None
    batch_size = 100
    
    while True:
        # Scroll with offset
        results = client.scroll(
            collection_name=CFG.qdrant_collection,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        
        points, next_offset = results
        
        if not points:
            break
        
        # Extract document data
        for point in points:
            payload = point.payload or {}
            
            # Get text from various possible fields
            text = (
                payload.get('text') or
                payload.get('chunk_text') or
                payload.get('content') or
                ""
            )
            
            if not text:
                print(f"⚠️  Warning: Point {point.id} has no text content, skipping")
                continue
            
            # Extract metadata
            metadata = {
                'dtad_id': payload.get('dtad_id'),
                'title': payload.get('title'),
                'source_path': payload.get('source_path'),
                'page_start': payload.get('page_start'),
                'page_end': payload.get('page_end'),
                'region': payload.get('region'),
                'date': payload.get('publication_date'),
            }
            
            documents.append({
                'id': str(point.id),
                'text': text,
                'metadata': metadata,
            })
        
        print(f"  Fetched {len(documents)}/{total_docs} documents...", end='\r')
        
        # Check if we're done
        if next_offset is None:
            break
        
        offset = next_offset
    
    print(f"\n✅ Fetched {len(documents)} documents with text content")
    return documents


def main():
    """Build and save BM25 index."""
    print("=" * 70)
    print("🔨 Building BM25 Index for Hybrid Search")
    print("=" * 70)
    print()
    
    # Fetch documents from Qdrant
    documents = fetch_all_documents()
    
    if not documents:
        print("❌ No documents found! Cannot build index.")
        sys.exit(1)
    
    # Build BM25 index
    print()
    print("🔨 Building BM25 index...")
    index = BM25Index()
    index.build_index(documents)
    
    # Save index
    output_path = CFG.state_dir / "bm25_index.pkl"
    print()
    print(f"💾 Saving index to {output_path}...")
    index.save(output_path)
    
    # Summary
    print()
    print("=" * 70)
    print("✅ BM25 Index Built Successfully!")
    print("=" * 70)
    print(f"📁 Location: {output_path}")
    print(f"📊 Documents indexed: {len(documents)}")
    print(f"💾 File size: {output_path.stat().st_size / 1024:.1f} KB")
    print()
    print("🎉 Hybrid search is now ready to use!")
    print()
    print("Next steps:")
    print("  1. Set use_hybrid=True in core/config.py (already default)")
    print("  2. Restart Streamlit: streamlit run ui/app_streamlit.py")
    print("  3. Test with exact keyword queries like 'IT-Projekte' or 'CPV 45000000'")
    print()


if __name__ == "__main__":
    main()
