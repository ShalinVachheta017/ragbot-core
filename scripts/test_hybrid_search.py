"""
Test hybrid search vs dense-only search.

Compare results for queries that should benefit from keyword matching.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import CFG
from core.search import search_dense, search_hybrid
from core.qa import retrieve_candidates


def test_query(query: str, show_top_n: int = 3):
    """Test a single query with both dense and hybrid search."""
    print(f"\n{'=' * 70}")
    print(f"🔍 Query: {query}")
    print(f"{'=' * 70}")
    
    # Dense-only search
    print("\n📊 Dense Search (Vector only):")
    print("-" * 70)
    try:
        dense_results = search_dense(query, limit=10)
        if dense_results:
            for i, result in enumerate(dense_results[:show_top_n], 1):
                payload = result.payload or {}
                title = payload.get('title', 'No title')[:60]
                dtad = payload.get('dtad_id', 'N/A')
                score = result.score or 0.0
                print(f"  {i}. [{score:.3f}] DTAD-{dtad} | {title}")
        else:
            print("  ❌ No results")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Hybrid search
    print("\n🔥 Hybrid Search (BM25 + Vector):")
    print("-" * 70)
    try:
        hybrid_results = search_hybrid(query, limit=10)
        if hybrid_results:
            for i, result in enumerate(hybrid_results[:show_top_n], 1):
                payload = result.payload or {}
                title = payload.get('title', 'No title')[:60]
                dtad = payload.get('dtad_id', 'N/A')
                score = result.score or 0.0
                print(f"  {i}. [{score:.3f}] DTAD-{dtad} | {title}")
        else:
            print("  ❌ No results")
    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    """Run test queries."""
    print("=" * 70)
    print("🧪 Testing Hybrid Search vs Dense Search")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Qdrant Collection: {CFG.qdrant_collection}")
    print(f"  use_hybrid: {CFG.use_hybrid}")
    print(f"  Top-K: {CFG.final_k}")
    
    # Test queries from BASELINE_ANALYSIS.md (known failures)
    test_queries = [
        # Exact keyword queries (should benefit most from hybrid)
        "IT-Projekte Tender",
        "Sanierungsarbeiten Vergaben",
        "CPV 45000000",
        
        # Exact match (already works, but hybrid might improve)
        "Was ist DTAD-ID 20046891?",
        
        # Semantic queries (dense should still work well)
        "Garten- und Landschaftsbau Ausschreibungen",
        "VOB requirements",
    ]
    
    for query in test_queries:
        test_query(query, show_top_n=5)
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Testing Complete!")
    print("=" * 70)
    print("\n💡 Observations:")
    print("  - Hybrid search should show better results for exact keyword queries")
    print("  - Dense search still works well for semantic/fuzzy queries")
    print("  - Check if 'IT-Projekte' and 'Sanierungsarbeiten' now return results")
    print()


if __name__ == "__main__":
    main()
