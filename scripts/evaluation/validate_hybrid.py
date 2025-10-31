"""
Quick validation that hybrid search is working.
This script tests the integration without complex dependencies.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

print("=" * 70)
print("🧪 Hybrid Search Validation")
print("=" * 70)

# Test 1: Check BM25 index exists and loads
print("\n1️⃣  Checking BM25 index...")
try:
    from core.hybrid_search import get_bm25_index
    index = get_bm25_index()
    print(f"   ✅ BM25 index loaded: {len(index.doc_ids)} documents")
except Exception as e:
    print(f"   ❌ Failed to load BM25 index: {e}")
    sys.exit(1)

# Test 2: Check configuration
print("\n2️⃣  Checking configuration...")
try:
    from core.config import CFG
    print(f"   ✅ use_hybrid: {CFG.use_hybrid}")
    print(f"   ✅ Qdrant collection: {CFG.qdrant_collection}")
    print(f"   ✅ Top-K: {CFG.final_k}")
except Exception as e:
    print(f"   ❌ Configuration error: {e}")
    sys.exit(1)

# Test 3: Test BM25 search
print("\n3️⃣  Testing BM25 keyword search...")
try:
    from core.hybrid_search import search_bm25
    
    # Test queries that should benefit from keyword matching
    test_queries = [
        "IT-Projekte",
        "Sanierungsarbeiten",
        "CPV 45000000",
    ]
    
    for query in test_queries:
        results = search_bm25(query, top_k=5)
        print(f"   Query: '{query}' → {len(results)} results")
        if results:
            top_doc_id, top_score = results[0]
            print(f"     Top result: {top_doc_id} (score: {top_score:.4f})")
        else:
            print(f"     ⚠️  No results")
    
    print("   ✅ BM25 search working")
except Exception as e:
    print(f"   ❌ BM25 search failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test hybrid search integration
print("\n4️⃣  Testing hybrid search integration...")
try:
    from core.search import search_hybrid
    
    query = "IT-Projekte Tender"
    print(f"   Query: '{query}'")
    results = search_hybrid(query, limit=5)
    print(f"   ✅ Hybrid search returned {len(results)} results")
    
    if results:
        for i, result in enumerate(results[:3], 1):
            payload = result.payload or {}
            dtad = payload.get('dtad_id', 'N/A')
            title = (payload.get('title', 'No title') or '')[:50]
            print(f"     {i}. DTAD-{dtad}: {title}...")
    
except Exception as e:
    print(f"   ❌ Hybrid search failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test QA pipeline
print("\n5️⃣  Testing full QA pipeline with hybrid search...")
try:
    from core.qa import retrieve_candidates
    
    test_query = "Sanierungsarbeiten Vergaben"
    print(f"   Query: '{test_query}'")
    hits = retrieve_candidates(test_query)
    print(f"   ✅ Retrieved {len(hits)} candidate hits")
    
    if hits:
        for i, hit in enumerate(hits[:3], 1):
            dtad = hit.payload.get('dtad_id', 'N/A')
            title = (hit.payload.get('title', 'No title') or '')[:50]
            print(f"     {i}. DTAD-{dtad}: {title}... (score: {hit.score:.3f})")
    
except Exception as e:
    print(f"   ❌ QA pipeline failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("✅ All Tests Passed!")
print("=" * 70)
print("\n🎉 Hybrid search is fully integrated and working!")
print()
print("Next steps:")
print("  1. Restart Streamlit UI to test interactively")
print("  2. Try these queries that previously failed:")
print("     - 'IT-Projekte Tender'")
print("     - 'Sanierungsarbeiten Vergaben'")
print("     - 'CPV 45000000'")
print()
