from core.index import Indexer
from core.io import PDFLoader
from core.config import CFG
from pathlib import Path
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
import torch

def find_skipped_files(extract_dir: Path, log_file: Path = None) -> list[Path]:
    """Find PDF files that were previously skipped (no text extracted)"""
    skipped_files = []
    
    # Get all PDF files
    all_pdfs = list(extract_dir.rglob("*.pdf"))
    
    # Test each file to see if it has extractable text
    loader_no_ocr = PDFLoader(use_ocr=False)
    
    for pdf in all_pdfs:
        try:
            pages = loader_no_ocr.load_pages(pdf)
            if not pages:  # No pages extracted = was likely skipped
                skipped_files.append(pdf)
        except Exception:
            skipped_files.append(pdf)  # If error, try with OCR
    
    return skipped_files

def main():
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 Finding previously skipped PDF files...")
    
    extract_dir = Path(CFG.extract_dir)
    skipped_files = find_skipped_files(extract_dir)
    
    print(f"📄 Found {len(skipped_files)} files to process with OCR:")
    for f in skipped_files[:10]:  # Show first 10
        print(f"  - {f.name}")
    if len(skipped_files) > 10:
        print(f"  ... and {len(skipped_files) - 10} more")
    
    if not skipped_files:
        print("✅ No skipped files found! All documents already processed.")
        return
    
    # Initialize components with OCR enabled
    cfg = CFG
    loader = PDFLoader(use_ocr=True)  # Enable OCR
    
    # Initialize indexer components
    indexer = Indexer(cfg)
    
    print(f"🚀 Starting OCR processing of {len(skipped_files)} files...")
    
    new_chunks_count = 0
    processed_files = 0
    
    for i, pdf_path in enumerate(skipped_files, 1):
        try:
            print(f"🔄 OCR Processing {i}/{len(skipped_files)}: {pdf_path.name}")
            
            # Load pages with OCR
            pages = loader.load_pages(pdf_path)
            
            if not pages:
                print(f"⏭️  Still no text after OCR: {pdf_path.name}")
                continue
            
            # Chunk the pages
            chunks = indexer.chunker.split(pages)
            
            if not chunks:
                print(f"⏭️  No chunks created: {pdf_path.name}")
                continue
            
            # Generate document hash
            try:
                h = indexer._hash_file(pdf_path)
            except:
                import hashlib
                h = hashlib.sha1(str(pdf_path).encode("utf-8")).hexdigest()
            
            # Prepare for embedding
            payloads, texts = [], []
            for c in chunks:
                meta = indexer.joiner.enrich(c.source_path, {**c.meta})
                pl = {
                    **c.payload(),
                    **meta,
                    "doc_hash": h,
                    "text": c.text[:1500],  # Store text for reranker
                    "processed_with_ocr": True  # Flag OCR processing
                }
                payloads.append(pl)
                texts.append(c.text)
            
            # Generate embeddings
            vecs = indexer._embed(texts)
            
            # Create points for Qdrant
            points = []
            for v, pl in zip(vecs, payloads):
                points.append(models.PointStruct(
                    id=indexer._point_id(pl["doc_hash"], pl["chunk_idx"]),
                    vector=v.tolist(),
                    payload=pl,
                ))
            
            # Add to existing collection (don't recreate!)
            indexer.client.upsert(
                collection_name=cfg.qdrant_collection,
                points=points,
                wait=False
            )
            
            print(f"✅ Added {len(chunks)} chunks from {pdf_path.name}")
            new_chunks_count += len(chunks)
            processed_files += 1
            
            # Clear GPU cache periodically
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")
            continue
    
    # Final OCR statistics
    ocr_stats = loader.get_ocr_stats()
    
    print(f"\n🎉 OCR Processing Complete!")
    print(f"📊 Files processed: {processed_files}")
    print(f"📊 New chunks added: {new_chunks_count}")
    print(f"📊 OCR attempts: {ocr_stats['attempted']}")
    print(f"📊 OCR successful: {ocr_stats['successful']}")
    print(f"📊 OCR failed: {ocr_stats['failed']}")
    
    if new_chunks_count > 0:
        print(f"🚀 Your German document RAG system now has enhanced coverage!")
        print(f"💡 Test with: python -m scripts.search")

if __name__ == "__main__":
    main()
