#!/usr/bin/env python3
# scripts/embed.py

"""
Index builder CLI for your German tender RAG corpus.

Modes
- fresh     : drop & recreate the collection, then index everything
- append    : keep the existing collection; idempotent upserts by deterministic IDs
- ocr-only  : only process PDFs that previously yielded no text and try OCR

Extras
- Qdrant health check (/readyz)
- Config overrides from CLI (batch size, flush size, chunking, collection)
- Safe GPU/CPU prints
"""

from __future__ import annotations
import argparse
import sys
import time
import logging
from pathlib import Path

# Optional: used for readyz check; degrade gracefully if missing
try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

# Ensure repo root and core/* are importable when running from anywhere
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import CFG
from core.index import Indexer  # updated indexer supports fresh/append/ocr-only


def _qdrant_ready(url: str, timeout_s: float = 3.0) -> bool:
    if not _HAS_REQUESTS:
        # If requests isn't available, skip the check rather than failing.
        return True
    try:
        r = requests.get(url.rstrip("/") + "/readyz", timeout=timeout_s)
        # The /readyz endpoint returns 200 OK when ready. The text content can vary.
        return r.ok
    except Exception:
        return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build or update the Qdrant index for the tender RAG system."
    )
    p.add_argument(
        "--mode",
        choices=["fresh", "append", "ocr-only"],
        default="fresh",
        help="fresh: recreate collection; append: keep collection; ocr-only: only reprocess OCR-needy PDFs",
    )
    p.add_argument("--collection", type=str, default=CFG.qdrant_collection,
                   help="Target Qdrant collection name")
    p.add_argument("--batch", type=int, default=CFG.embed_batch_size,
                   help="Embedding batch size")
    p.add_argument("--flush", type=int, default=CFG.embed_flush_chunks,
                   help="#points to buffer before upsert")
    p.add_argument("--chunk-size", type=int, default=CFG.chunk_size,
                   help="Chunk size (chars)")
    p.add_argument("--chunk-overlap", type=int, default=CFG.chunk_overlap,
                   help="Chunk overlap (chars)")
    p.add_argument("--extract-dir", type=str, default=str(CFG.extract_dir),
                   help="Where PDF files are located")
    p.add_argument("--no-health-check", action="store_true",
                   help="Skip Qdrant /readyz check")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Verbose logging")
    return p.parse_args()


def main():
    args = parse_args()

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # Apply CLI overrides onto CFG (in-memory)
    CFG.qdrant_collection = args.collection
    CFG.embed_batch_size = int(args.batch)
    CFG.embed_flush_chunks = int(args.flush)
    CFG.chunk_size = int(args.chunk_size)
    CFG.chunk_overlap = int(args.chunk_overlap)
    extract_dir = Path(args.extract_dir)

    print("🧩 Config:")
    print(f"   • collection        : {CFG.qdrant_collection}")
    print(f"   • embed_model       : {CFG.embed_model}")
    print(f"   • embed_dim         : {CFG.embed_dim}")
    print(f"   • batch/flush       : {CFG.embed_batch_size}/{CFG.embed_flush_chunks}")
    print(f"   • chunk size/overlap: {CFG.chunk_size}/{CFG.chunk_overlap}")
    print(f"   • extract dir       : {extract_dir}")

    # Qdrant health
    if not args.no_health_check:
        ok = _qdrant_ready(CFG.qdrant_url)
        if not ok:
            print(f"❌ Qdrant not ready at {CFG.qdrant_url}/readyz")
            print("   Tip: ensure the Qdrant server is running.")
            sys.exit(2)
        print("✅ Qdrant /readyz OK")

    t0 = time.time()

    try:
        if args.mode == "ocr-only":
            print("🔁 Mode: OCR-only (no collection recreation)")
            indexer = Indexer(CFG, fresh=False)
            indexer.build_ocr_only(extract_dir=extract_dir)
        else:
            fresh = (args.mode == "fresh")
            print(f"🏗️ Mode: {'fresh (recreate collection)' if fresh else 'append (keep collection)'}")
            indexer = Indexer(CFG, fresh=fresh)
            indexer.build(extract_dir=extract_dir)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Index build failed: {e}")
        sys.exit(1)

    dt = time.time() - t0
    print(f"🎉 Done in {dt:.1f}s")

if __name__ == "__main__":
    main()
