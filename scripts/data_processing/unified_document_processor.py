#!/usr/bin/env python3
"""
Unified Document Processor — extraction + sanity checks + smoke tests.

What it does now (no indexing step yet):
  1) Extract all ZIPs from data/raw into data/extract (safe, nested ZIP aware)
  2) (Optional) Clean latest Excel -> metadata/cleaned_metadata.{xlsx,csv}
  3) Categorize extracted files by type
  4) Load PDFs with native text; fall back to OCR when needed (stats only)
  5) If Qdrant collection has points, run retrieval smoke tests
  6) Print a clean summary with next-step guidance

When you’re ready to actually index, we’ll wire in the embedding/index pipeline
(core/embed.py or core/index.py) as step 5 before the smoke tests.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Make repo-root and core importable when running directly
ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "core"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from core.config import CFG
from core.io import PDFLoader, ZipIngestor, ExcelCleaner
from core.qa import retrieve_candidates
from core.search import is_alive, count_points  # health + collection stats


class UnifiedDocumentProcessor:
    """Extraction + OCR + checks. Indexing comes later."""

    def __init__(self):
        self.stats = {
            "pdf_regular": {"files": 0, "chunks": 0, "success": 0},
            "pdf_ocr":     {"files": 0, "chunks": 0, "success": 0},
            "doc_files":   {"files": 0, "chunks": 0, "success": 0},
            "total_processed": 0,
        }

    # ---------- Stage 1: extraction ----------

    def extract_documents(self) -> int:
        print("📦 Starting document extraction…")
        try:
            ingestor = ZipIngestor()
            files_extracted = ingestor.run()
            print(f"✅ Extracted {files_extracted} files")
            return files_extracted
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return 0

    # ---------- Stage 1b: excel cleaning (optional but useful) ----------

    def clean_latest_excel(self) -> Path | None:
        try:
            cleaner = ExcelCleaner()
            out = cleaner.run()
            print(f"🧽 Excel cleaned → {out}")
            return out
        except FileNotFoundError:
            print("ℹ️  No .xlsx found in data/raw — skipping Excel cleaning.")
        except Exception as e:
            print(f"⚠️ Excel cleaning failed: {e}")
        return None

    # ---------- Stage 2: categorize ----------

    def categorize_files(self) -> Dict[str, List[Path]]:
        print("\n📂 Categorizing files by type…")
        all_files = list(Path(CFG.extract_dir).rglob("*"))

        cats = {"pdf": [], "doc": [], "docx": [], "ppt": [], "other": []}
        for fp in all_files:
            if not fp.is_file():
                continue
            sfx = fp.suffix.lower()
            if sfx == ".pdf":
                cats["pdf"].append(fp)
            elif sfx == ".doc":
                cats["doc"].append(fp)
            elif sfx == ".docx":
                cats["docx"].append(fp)
            elif sfx in (".ppt", ".pptx"):
                cats["ppt"].append(fp)
            elif sfx in (".txt", ".rtf"):
                cats["other"].append(fp)

        print(f"📄 PDF:  {len(cats['pdf'])}")
        print(f"📝 DOC:  {len(cats['doc'])}")
        print(f"📝 DOCX: {len(cats['docx'])}")
        print(f"📊 PPT:  {len(cats['ppt'])}")
        print(f"📎 Other:{len(cats['other'])}")
        return cats

    # ---------- Stage 3: PDF processing (regular + OCR fallback) ----------

    def process_pdfs_unified(self, pdf_files: List[Path]) -> int:
        print(f"\n🧠 Processing {len(pdf_files)} PDFs (regular + OCR fallback)…")
        if not pdf_files:
            return 0

        reg_loader = PDFLoader(use_ocr=False)
        ocr_loader = PDFLoader(use_ocr=True)

        successful = 0
        for i, pdf in enumerate(pdf_files, start=1):
            print(f"  📄 [{i}/{len(pdf_files)}] {pdf.name}")
            try:
                # Try native text first
                pages = reg_loader.load_pages(pdf)
                if pages and any(len(p.text.strip()) > 50 for p in pages):
                    char_count = sum(len(p.text) for p in pages)
                    successful += 1
                    self.stats["pdf_regular"]["success"] += 1
                    self.stats["pdf_regular"]["chunks"] += len(pages)
                    print(f"    ✅ Regular: {len(pages)} pages, {char_count} chars")
                    continue

                # Fallback OCR
                print("    🔍 Trying OCR…")
                t0 = time.time()
                ocr_pages = ocr_loader.load_pages(pdf)
                dt = time.time() - t0
                if ocr_pages and any(len(p.text.strip()) > 20 for p in ocr_pages):
                    char_count = sum(len(p.text) for p in ocr_pages)
                    successful += 1
                    self.stats["pdf_ocr"]["success"] += 1
                    self.stats["pdf_ocr"]["chunks"] += len(ocr_pages)
                    print(f"    ✅ OCR: {len(ocr_pages)} pages, {char_count} chars ({dt:.1f}s)")
                else:
                    print(f"    ⚠️ No text extracted (OCR {dt:.1f}s)")
            except Exception as e:
                print(f"    ❌ Error: {e}")

        self.stats["pdf_regular"]["files"] = len(pdf_files)
        self.stats["pdf_ocr"]["files"] = len(pdf_files)
        return successful

    # ---------- Stage 4: Office docs (quick pass for stats only) ----------

    def process_office_docs(self, doc_files: List[Path], docx_files: List[Path], ppt_files: List[Path]) -> int:
        files = doc_files + docx_files + ppt_files
        print(f"\n📝 Processing {len(files)} Office files (lightweight stats)…")
        if not files:
            return 0

        ok = 0
        for i, f in enumerate(files, start=1):
            print(f"  📄 [{i}/{len(files)}] {f.name}")
            try:
                sfx = f.suffix.lower()
                if sfx == ".docx":
                    try:
                        import docx  # optional
                        doc = docx.Document(f)
                        text = "\n".join(p.text for p in doc.paragraphs)
                        if len(text.strip()) > 50:
                            ok += 1
                            self.stats["doc_files"]["chunks"] += 1
                            print(f"    ✅ DOCX: {len(text)} chars")
                        else:
                            print("    ⚠️ No substantial text")
                    except Exception as e:
                        print(f"    ⚠️ python-docx not available or failed: {e}")

                elif sfx in (".ppt", ".pptx"):
                    print("    ℹ️ PPT requires python-pptx (skipping content read).")

                else:  # .doc or others
                    print("    ℹ️ DOC legacy format not parsed here (requires extra tooling).")

            except Exception as e:
                print(f"    ❌ Error: {e}")

        self.stats["doc_files"]["files"] = len(files)
        self.stats["doc_files"]["success"] = ok
        return ok

    # ---------- Stage 5: (future) indexing ----------

    def show_index_status(self) -> int:
        """Report Qdrant health + collection points, but do NOT build index here."""
        print("\n🏷️  Qdrant / Collection status")
        if not is_alive():
            print(f"❌ Qdrant at {CFG.qdrant_url} is not reachable. Start it first.")
            return -1
        try:
            pts = count_points()
            if pts is None:
                print(f"ℹ️  Collection '{CFG.qdrant_collection}' not found.")
                return 0
            print(f"✅ Collection '{CFG.qdrant_collection}': {pts} points")
            return int(pts)
        except Exception as e:
            print(f"⚠️ Could not read collection status: {e}")
            return -1

    # ---------- Stage 6: retrieval smoke tests (only if points exist) ----------

    def test_system(self) -> Dict[str, Any]:
        print("\n🧪 Retrieval smoke tests")
        tests = [
            "Mindestlohn Bestimmungen Bauprojekte",
            "Vergabeunterlagen Straßenbau",
            "VOB Regelungen",
            "construction requirements",
            "technical specifications",
        ]
        results = {"queries_tested": len(tests), "successful_queries": 0, "total_hits": 0}

        points = self.show_index_status()
        if points <= 0:
            print("ℹ️  Skipping smoke tests because the collection has no points yet.")
            return results

        for i, q in enumerate(tests, start=1):
            print(f"  🔎 [{i}/{len(tests)}] {q!r}")
            try:
                hits = retrieve_candidates(q, CFG)
                if hits:
                    results["successful_queries"] += 1
                    results["total_hits"] += len(hits)
                    print(f"    ✅ {len(hits)} hits (top score ~ {float(hits[0].score):.3f})")
                else:
                    print("    ⚠️ No hits")
            except Exception as e:
                print(f"    ❌ Error: {e}")
        return results

    # ---------- Orchestrator ----------

    def run_unified_pipeline(self):
        print("🚀 Unified Document Processing Pipeline")
        print("🎯 PDF (regular + OCR) + basic Office stats (indexing later)")
        print("=" * 70)

        t0 = time.time()

        # Stage 1: Extract
        extracted = self.extract_documents()

        # Stage 1b: Excel cleaning (optional)
        self.clean_latest_excel()

        # Stage 2: Categorize
        cats = self.categorize_files()

        # Stage 3: Process PDFs
        pdf_ok = self.process_pdfs_unified(cats["pdf"])

        # Stage 4: Office docs (stats-only)
        office_ok = self.process_office_docs(cats["doc"], cats["docx"], cats["ppt"])

        # Stage 5: Show index status (no index build here)
        pts = self.show_index_status()

        # Stage 6: Smoke tests (only if collection has points)
        smoke = self.test_system() if (pts and pts > 0) else {"queries_tested": 0, "successful_queries": 0, "total_hits": 0}

        dt = time.time() - t0
        total_chunks = (
            self.stats["pdf_regular"]["chunks"] +
            self.stats["pdf_ocr"]["chunks"] +
            self.stats["doc_files"]["chunks"]
        )
        total_files = pdf_ok + office_ok

        print("\n" + "=" * 70)
        print("🎉 PIPELINE COMPLETE")
        print("=" * 70)
        print("📊 Processing Summary")
        print(f"   📄 PDF (Regular): {self.stats['pdf_regular']['success']} successful")
        print(f"   🔍 PDF (OCR):    {self.stats['pdf_ocr']['success']} successful")
        print(f"   📝 Office docs:  {self.stats['doc_files']['success']} successful")
        print("\n🎯 Totals")
        print(f"   📁 Files processed successfully: {total_files}")
        print(f"   🔢 Estimated chunks (pages):     {total_chunks}")
        print(f"   ⏱️  Total time:                  {dt:.1f}s")
        if pts is None:
            print(f"   📦 Collection: not found → {CFG.qdrant_collection}")
        elif pts < 0:
            print("   📦 Collection: unknown (Qdrant not reachable)")
        else:
            print(f"   📦 Collection points:            {pts}")

        if smoke["queries_tested"] > 0:
            print(f"   🧪 Smoke tests: {smoke['successful_queries']}/{smoke['queries_tested']} passed, total hits {smoke['total_hits']}")
        else:
            print("   🧪 Smoke tests: skipped (no points yet)")

        print("\nNext steps:")
        print("  1) Run the embedding/indexing pipeline to populate Qdrant (to be added).")
        print("  2) Then try:  streamlit run ui/multilingual_tender_bot.py")
        print("  3) Health check: curl http://127.0.0.1:6333/readyz  (expect 'ok')")

def main():
    UnifiedDocumentProcessor().run_unified_pipeline()

if __name__ == "__main__":
    main()
