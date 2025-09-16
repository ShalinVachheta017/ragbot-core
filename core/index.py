# core/index.py

from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import logging, hashlib
import numpy as np
import torch
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from .domain import DocumentPage, DocumentChunk
from .io import PDFLoader, ExcelMetadataJoiner
from .config import CFG
from uuid import uuid5, NAMESPACE_URL

class PageAwareChunker:
    def __init__(self, size: int, overlap: int):
        self.size, self.overlap = size, overlap

    def split(self, pages: List[DocumentPage]) -> List[DocumentChunk]:
        text_acc, page_acc, chunks = [], [], []
        idx = 0

        def flush():
            nonlocal idx, text_acc, page_acc
            if not text_acc:
                return
            text = "".join(text_acc)
            page_start, page_end = page_acc[0], page_acc[-1]
            chunks.append(DocumentChunk(
                chunk_index=idx,
                text=text,
                source_path=pages[0].source_path if pages else None,
                page_start=page_start,
                page_end=page_end,
                meta={}
            ))
            idx += 1
            keep = text[-self.overlap:] if self.overlap > 0 else ""
            text_acc = [keep]
            page_acc = [page_end] if self.overlap > 0 else []

        for p in pages:
            t = p.text or ""
            if not t:
                continue
            cursor = 0
            while cursor < len(t):
                space_left = self.size - sum(len(x) for x in text_acc)
                if space_left <= 0:
                    flush()
                    space_left = self.size
                take = t[cursor: cursor + space_left]
                text_acc.append(take)
                if p.page_number not in page_acc:
                    page_acc.append(p.page_number)
                cursor += len(take)
        flush()
        return chunks

class Indexer:
    def __init__(self, cfg=CFG):
        self.cfg = cfg
        self.loader = PDFLoader()  # Will be overridden for OCR processing
        self.chunker = PageAwareChunker(cfg.chunk_size, cfg.chunk_overlap)

        # 🚀 FORCE GPU USAGE - Explicit device assignment
        if torch.cuda.is_available():
            device = 'cuda'
            print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
            print(f"✅ GPU Memory: {torch.cuda.get_device_properties(0).total_memory // (1024**3)}GB")
        else:
            device = 'cpu'
            print("⚠️  Using CPU - GPU not available")

        # Load embedder with explicit device
        self.embedder = SentenceTransformer(
            cfg.embed_model,
            device=device,
            trust_remote_code=True
        )

        # 🚀 CRITICAL: Force GPU placement and FP16 precision
        if device == 'cuda':
            self.embedder = self.embedder.cuda()  # Ensure GPU placement
            self.embedder = self.embedder.half()  # FP16 for 2x speed + 50% memory
            print("✅ Embedder loaded on GPU with FP16 precision")

        # Initialize Qdrant client with gRPC for speed
        self.client = QdrantClient(
            url=cfg.qdrant_url,
            grpc_port=6334,
            prefer_grpc=True
        )

        # 🗑️ DELETE OLD COLLECTION AND CREATE FRESH ONE
        self._clean_and_create_collection(cfg.embed_dim)
        self.joiner = ExcelMetadataJoiner()

    def _cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def _clean_and_create_collection(self, dim: int):
        """🗑️ Delete old collection and create fresh one"""
        try:
            # Delete existing collection
            self.client.delete_collection(self.cfg.qdrant_collection)
            print(f"🗑️  Deleted old collection: {self.cfg.qdrant_collection}")
        except Exception as e:
            print(f"ℹ️  No existing collection to delete: {e}")

        # Create fresh collection with optimized settings
        self.client.create_collection(
            collection_name=self.cfg.qdrant_collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=64),
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=20000),
            on_disk_payload=False  # Keep in memory for speed
        )
        print(f"✅ Created fresh collection: {self.cfg.qdrant_collection} (dim={dim})")

    def _embed(self, texts: list[str]) -> np.ndarray:
        """🚀 FORCE GPU embedding with memory management and Matryoshka cropping"""
        # Clear GPU cache before embedding
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # 🚀 FORCE GPU COMPUTATION with mixed precision
        if torch.cuda.is_available():
            with torch.cuda.amp.autocast():
                out = self.embedder.encode(
                    texts,
                    batch_size=self.cfg.embed_batch_size,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=True
                )
        else:
            out = self.embedder.encode(
                texts,
                batch_size=self.cfg.embed_batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=True
            )

        # 🔧 CRITICAL: Matryoshka dimension cropping to 512
        out = np.asarray(out, dtype="float32")
        if out.shape[1] > self.cfg.embed_dim:
            out = out[:, :self.cfg.embed_dim]
            print(f"📐 Cropped embeddings from {out.shape[1]} to {self.cfg.embed_dim} dimensions")

        # Clear GPU cache after embedding
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return out

    def _point_id(self, doc_hash: str, chunk_idx: int) -> str:
        """Generate deterministic UUID for points"""
        return str(uuid5(NAMESPACE_URL, f"{doc_hash}|{chunk_idx}"))

    def _hash_file(self, pdf_path: Path) -> str:
        """🆕 NEW: Generate hash for a file - needed for OCR processing"""
        try:
            return hashlib.sha1(pdf_path.read_bytes()).hexdigest()
        except Exception:
            # Fallback to path-based hash if file can't be read
            return hashlib.sha1(str(pdf_path).encode("utf-8")).hexdigest()

    def build(self, extract_dir: Path | None = None, metadata_path: Path | None = None):
        """🚀 Build index with GPU acceleration and batch processing"""
        base = Path(extract_dir or self.cfg.extract_dir)
        pdfs = sorted(base.rglob("*.pdf"))
        
        print(f"📄 Found {len(pdfs)} PDFs to process")
        
        if not pdfs:
            print("⚠️  No PDF files found in extract directory")
            return

        # Initialize processing variables
        BUFFER_SIZE = self.cfg.embed_flush_chunks
        points_buffer = []
        total_chunks = 0
        processed_files = 0

        for pdf_idx, pdf in enumerate(pdfs):
            try:
                print(f"🔄 Processing PDF {pdf_idx + 1}/{len(pdfs)}: {pdf.name}")
                
                # Load and chunk document
                pages = self.loader.load_pages(pdf)
                chunks: List[DocumentChunk] = self.chunker.split(pages)

                if not chunks:
                    print(f"⏭️  Skipped (no text): {pdf.name}")
                    continue

                # Generate document hash using the new method
                h = self._hash_file(pdf)

                # Prepare payloads and texts for embedding
                payloads, texts = [], []
                for c in chunks:
                    meta = self.joiner.enrich(c.source_path, {**c.meta})
                    pl = {
                        **c.payload(),
                        **meta,
                        "doc_hash": h,
                        "text": c.text[:1500]  # Store text snippet for reranker
                    }
                    payloads.append(pl)
                    texts.append(c.text)

                # 🚀 Process in GPU-optimized batches
                batch_size = min(len(texts), self.cfg.embed_batch_size * 4)
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    batch_payloads = payloads[i:i + batch_size]
                    
                    # Generate embeddings on GPU
                    vecs = self._embed(batch_texts)
                    
                    # Add to upload buffer
                    for v, pl in zip(vecs, batch_payloads):
                        points_buffer.append(models.PointStruct(
                            id=self._point_id(pl["doc_hash"], pl["chunk_idx"]),
                            vector=v.tolist(),
                            payload=pl,
                        ))

                    # 🚀 Batch upsert when buffer is full
                    if len(points_buffer) >= BUFFER_SIZE:
                        self.client.upsert(
                            collection_name=self.cfg.qdrant_collection,
                            points=points_buffer,
                            wait=False  # Non-blocking for speed
                        )
                        print(f"📤 Uploaded batch: {len(points_buffer)} points")
                        total_chunks += len(points_buffer)
                        points_buffer.clear()

                        # Clear GPU memory after batch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()

                processed_files += 1
                print(f"✅ Processed {len(chunks)} chunks from {pdf.name}")

            except Exception as e:
                print(f"❌ Error processing {pdf.name}: {e}")
                continue

        # 📤 Upload final batch
        if points_buffer:
            self.client.upsert(
                collection_name=self.cfg.qdrant_collection,
                points=points_buffer,
                wait=False
            )
            print(f"📤 Final upload: {len(points_buffer)} points")
            total_chunks += len(points_buffer)

        # Final cleanup
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print(f"🎉 Indexing complete!")
        print(f"📊 Processed: {processed_files}/{len(pdfs)} files")
        print(f"📊 Total chunks: {total_chunks}")
        print(f"🚀 Your German document RAG system is ready!")

    def build_ocr_only(self, extract_dir: Path | None = None, reprocess_skipped: bool = True):
        """🆕 NEW: Build index for OCR-only processing (doesn't recreate collection)"""
        base = Path(extract_dir or self.cfg.extract_dir)
        
        # Find files that were previously skipped (no extractable text)
        skipped_files = []
        loader_no_ocr = PDFLoader(use_ocr=False)
        
        for pdf in sorted(base.rglob("*.pdf")):
            try:
                pages = loader_no_ocr.load_pages(pdf)
                if not pages:  # No pages extracted = was likely skipped
                    skipped_files.append(pdf)
            except Exception:
                skipped_files.append(pdf)  # If error, try with OCR
        
        print(f"🔍 Found {len(skipped_files)} previously skipped files for OCR processing")
        
        if not skipped_files:
            print("✅ No skipped files found! All documents already processed.")
            return
        
        # Enable OCR for this processing
        self.loader = PDFLoader(use_ocr=True)
        
        # Process only the skipped files
        BUFFER_SIZE = self.cfg.embed_flush_chunks
        points_buffer = []
        new_chunks_count = 0
        processed_files = 0
        
        for i, pdf_path in enumerate(skipped_files, 1):
            try:
                print(f"🔄 OCR Processing {i}/{len(skipped_files)}: {pdf_path.name}")
                
                # Load pages with OCR
                pages = self.loader.load_pages(pdf_path)
                
                if not pages:
                    print(f"⏭️  Still no text after OCR: {pdf_path.name}")
                    continue
                
                # Chunk the pages
                chunks = self.chunker.split(pages)
                
                if not chunks:
                    print(f"⏭️  No chunks created: {pdf_path.name}")
                    continue
                
                # Generate document hash
                h = self._hash_file(pdf_path)
                
                # Prepare for embedding
                payloads, texts = [], []
                for c in chunks:
                    meta = self.joiner.enrich(c.source_path, {**c.meta})
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
                vecs = self._embed(texts)
                
                # Create points for Qdrant
                for v, pl in zip(vecs, payloads):
                    points_buffer.append(models.PointStruct(
                        id=self._point_id(pl["doc_hash"], pl["chunk_idx"]),
                        vector=v.tolist(),
                        payload=pl,
                    ))
                
                # Add to existing collection (don't recreate!)
                if len(points_buffer) >= BUFFER_SIZE:
                    self.client.upsert(
                        collection_name=self.cfg.qdrant_collection,
                        points=points_buffer,
                        wait=False
                    )
                    print(f"📤 Uploaded OCR batch: {len(points_buffer)} points")
                    new_chunks_count += len(points_buffer)
                    points_buffer.clear()
                
                print(f"✅ Added {len(chunks)} chunks from {pdf_path.name}")
                processed_files += 1
                
                # Clear GPU cache periodically
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
            except Exception as e:
                print(f"❌ Error processing {pdf_path.name}: {e}")
                continue
        
        # Final batch upload
        if points_buffer:
            self.client.upsert(
                collection_name=self.cfg.qdrant_collection,
                points=points_buffer,
                wait=False
            )
            print(f"📤 Final OCR upload: {len(points_buffer)} points")
            new_chunks_count += len(points_buffer)
        
        # Final OCR statistics
        if hasattr(self.loader, 'get_ocr_stats'):
            ocr_stats = self.loader.get_ocr_stats()
            print(f"\n🎉 OCR Processing Complete!")
            print(f"📊 Files processed: {processed_files}")
            print(f"📊 New chunks added: {new_chunks_count}")
            print(f"📊 OCR attempts: {ocr_stats['attempted']}")
            print(f"📊 OCR successful: {ocr_stats['successful']}")
            print(f"📊 OCR failed: {ocr_stats['failed']}")
        
        if new_chunks_count > 0:
            print(f"🚀 Your German document RAG system now has enhanced coverage!")
