#!/usr/bin/env python3
"""
Direct Embedding Pipeline - For Already Extracted Files
Skips extraction, processes files directly from data/extract
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
from core.index import Indexer
from core.io import PDFLoader
from core.qa import retrieve_candidates, answer_query
from core.config import CFG

def main():
    print("🔥 Direct Embedding Pipeline - Processing Extracted Files")
    print("🎯 Skipping extraction, using files in data/extract/")
    print("=" * 70)
    
    start_time = time.time()
    
    # Step 1: Verify files exist
    print("📂 Step 1: Checking extracted files...")
    
    all_files = list(CFG.extract_dir.rglob("*"))
    pdf_files = [f for f in all_files if f.suffix.lower() == '.pdf']
    docx_files = [f for f in all_files if f.suffix.lower() == '.docx']
    doc_files = [f for f in all_files if f.suffix.lower() == '.doc']
    
    total_files = len(pdf_files) + len(docx_files) + len(doc_files)
    
    print(f"   📄 PDF files: {len(pdf_files)}")
    print(f"   📝 DOCX files: {len(docx_files)}")
    print(f"   📋 DOC files: {len(doc_files)}")
    print(f"   📊 Total files: {total_files}")
    
    if total_files == 0:
        print("❌ No documents found in data/extract/")
        print("   Make sure your files are in: data/extract/")
        return False
    
    # Step 2: Build embeddings
    print(f"\n🧠 Step 2: Creating embeddings for {total_files} files...")
    
    try:
        # Initialize indexer with your optimized config
        indexer = Indexer(CFG)
        indexer.loader = PDFLoader(use_ocr=False)  # Regular processing first
        
        print("⚡ Starting embedding generation...")
        print(f"   🔧 Using: {CFG.embed_model}")
        print(f"   📏 Chunk size: {CFG.chunk_size}")
        print(f"   🔄 Overlap: {CFG.chunk_overlap}")
        print(f"   🎯 Hybrid search: {CFG.use_hybrid}")
        
        # Build the embeddings
        result = indexer.build()
        
        print("✅ Embeddings created successfully!")
        
    except Exception as e:
        print(f"❌ Embedding creation failed: {e}")
        return False
    
    # Step 3: Test embeddings
    print(f"\n🧪 Step 3: Testing embeddings with sample queries...")
    
    test_queries = [
        "Mindestlohn Bestimmungen Bauprojekte",
        "Vergabeunterlagen Straßenbau",
        "VOB Regelungen",
        "construction requirements",
        "technical specifications"
    ]
    
    successful_queries = 0
    
    for query in test_queries:
        try:
            hits = retrieve_candidates(query, CFG)
            if hits and len(hits) > 0:
                successful_queries += 1
                print(f"   ✅ '{query}': {len(hits)} results (score: {hits[0].score:.3f})")
            else:
                print(f"   ⚠️ '{query}': No results")
        except Exception as e:
            print(f"   ❌ '{query}': Error - {e}")
    
    # Final results
    total_time = time.time() - start_time
    success_rate = (successful_queries / len(test_queries)) * 100
    
    print("\n" + "=" * 70)
    print("🎉 DIRECT EMBEDDING PIPELINE COMPLETE!")
    print("=" * 70)
    print(f"📁 Files processed: {total_files}")
    print(f"⏱️ Processing time: {total_time:.1f} seconds")
    print(f"🧪 Test queries successful: {successful_queries}/{len(test_queries)} ({success_rate:.1f}%)")
    
    if successful_queries > 0:
        print(f"\n🚀 SUCCESS! Your embeddings are ready!")
        print(f"   Next: streamlit run ui/multilingual_tender_bot.py")
        return True
    else:
        print(f"\n⚠️ Embeddings created but queries not working")
        print(f"   Check configuration and try again")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎯 Your German construction document search is ready!")
    else:
        print("\n🔧 Check errors above and troubleshoot")
