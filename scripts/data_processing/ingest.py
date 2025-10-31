#!/usr/bin/env python3
"""
Ingestion Pipeline for German Tender RAG

This script orchestrates the extraction of ZIP archives and loose files from
`data/raw` to `data/extract`, cleans the latest Excel metadata into
`data/metadata/cleaned_metadata.xlsx`, and then triggers the indexing
pipeline via `scripts/embed.py`.

You can choose whether to recreate the collection from scratch (`--mode fresh`),
append to an existing collection (`--mode append`), or only process PDFs that
previously lacked text (`--mode ocr-only`).

Usage:
    python scripts/ingest.py --mode fresh
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse
import logging
import shutil
import subprocess
import sys

from core.config import CFG
from core.io import ZipIngestor, ExcelCleaner

def copy_loose_files() -> int:
    """
    Copy loose (non-zip) allowed files from raw_dir to extract_dir,
    preserving relative structure. Returns the number of files copied.
    """
    ALLOWED = {".pdf", ".docx", ".d83", ".dwg", ".jpg", ".png", ".tiff"}
    n = 0
    for p in CFG.raw_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in ALLOWED:
            rel = p.relative_to(CFG.raw_dir)
            dst = CFG.extract_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                # Copy only if new or updated
                if not dst.exists() or p.stat().st_mtime > dst.stat().st_mtime:
                    shutil.copy2(p, dst)
                    n += 1
            except Exception as e:
                logging.exception(f"Copy failed for {p}: {e}")
    return n

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the full ingestion pipeline and trigger indexing.")
    p.add_argument(
        "--mode",
        choices=["fresh", "append", "ocr-only"],
        default="fresh",
        help="fresh: recreate collection; append: keep collection; ocr-only: reprocess PDFs with no text",
    )
    p.add_argument(
        "--skip-clean",
        action="store_true",
        help="Skip Excel metadata cleaning",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging to stdout",
    )
    return p.parse_args()

def main():
    args = parse_args()

    # Configure logging
    CFG.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = CFG.logs_dir / f"ingest_run_{datetime.utcnow():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    if args.verbose:
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    logging.info("📦 Starting ingestion pipeline")
    print("📦 Extracting ZIPs (recursive) ...")
    ingestor = ZipIngestor()
    files_from_zip = ingestor.run()
    print(f"   ➜ extracted/analyzed from zips: {files_from_zip}")
    logging.info(f"Extracted/analyzed {files_from_zip} files from ZIP archives")

    print("📎 Copying loose files from data/raw -> data/extract ...")
    copied = copy_loose_files()
    print(f"   ➜ copied loose files: {copied}")
    logging.info(f"Copied {copied} loose files")

    if not args.skip_clean:
        try:
            print("📓 Cleaning latest Excel metadata (if present) ...")
            out = ExcelCleaner().run()
            print(f"   ➜ cleaned metadata at: {out}")
            logging.info(f"Cleaned metadata written to {out}")
        except FileNotFoundError:
            print("   ➜ no Excel metadata found, skipping")
            logging.info("No Excel metadata found; skipping cleaning")
        except Exception as e:
            logging.exception(f"Excel cleaning failed: {e}")
            print(f"   ➜ Excel cleaning failed: {e}")

    # Summary: how many PDFs are ready
    pdfs = sorted(CFG.extract_dir.rglob("*.pdf"))
    print(f"\n✅ Ready for embedding: {len(pdfs)} PDFs in {CFG.extract_dir}")
    logging.info(f"Ready for embedding: {len(pdfs)} PDFs")

    if not pdfs:
        print("   ⚠️  No PDFs found. Check data/raw, your zip contents, or allowed extensions.")
        logging.warning("No PDFs found after extraction; aborting indexing")
        return

    # Trigger the embedding/indexing stage via scripts/embed.py
    print(f"\n🏗️  Triggering indexing (mode={args.mode}) ...")
    try:
        subprocess.run(
            [sys.executable, "scripts/embed.py", "--mode", args.mode],
            check=True,
        )
        print("✅ Index build completed successfully")
        logging.info(f"Index build completed in mode={args.mode}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Index build failed: {e}")
        logging.error(f"Index build failed: {e}")

if __name__ == "__main__":
    main()
