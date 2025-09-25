# scripts/ingest.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import logging
import shutil

from core.config import CFG
from core.io import ZipIngestor, ExcelCleaner

def copy_loose_files():
    """
    Copy loose (non-zip) allowed files from raw_dir to extract_dir,
    preserving relative structure.
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
                if not dst.exists() or p.stat().st_mtime > dst.stat().st_mtime:
                    shutil.copy2(p, dst)
                    n += 1
            except Exception as e:
                logging.exception(f"Copy failed for {p}: {e}")
    return n

def main():
    CFG.logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(CFG.logs_dir / "ingest_run.log"),
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    print("📦 Extracting ZIPs (recursive) ...")
    ingestor = ZipIngestor()
    files_from_zip = ingestor.run()
    print(f"   ➜ extracted/analyzed from zips: {files_from_zip}")

    print("📎 Copying loose files from data/raw -> data/extract ...")
    copied = copy_loose_files()
    print(f"   ➜ copied loose files: {copied}")

    # Optional Excel cleaning (if any .xlsx exists)
    try:
        print("📓 Cleaning latest Excel metadata (if present) ...")
        out = ExcelCleaner().run()
        print(f"   ➜ cleaned metadata at: {out}")
    except FileNotFoundError:
        print("   ➜ no Excel metadata found, skipping")
    except Exception as e:
        logging.exception(f"Excel cleaning failed: {e}")
        print(f"   ➜ Excel cleaning failed: {e}")

    # Summary: how many PDFs are ready
    pdfs = sorted(CFG.extract_dir.rglob("*.pdf"))
    print(f"\n✅ Ready for embedding: {len(pdfs)} PDFs in {CFG.extract_dir}")
    if len(pdfs) == 0:
        print("   ⚠️  No PDFs found. Check data/raw, your zip contents, or allowed extensions.")

if __name__ == "__main__":
    main()
