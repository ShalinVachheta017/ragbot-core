# core/io.py
from __future__ import annotations
from pathlib import Path

from dataclasses import dataclass
import hashlib, json, csv, logging, zipfile
from datetime import datetime
from typing import Iterable, List, Optional, Tuple, Dict

from .domain import DocumentPage

import langdetect
import fitz  # PyMuPDF
import docx  # python-docx
import pandas as pd 

# 🆕 OCR imports
import pytesseract
from PIL import Image
import io

from .config import CFG

logging.basicConfig(
    filename=str(CFG.logs_dir / "data_preparation.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

@dataclass(frozen=True)
class FileInfo:
    path: Path
    size_mb: float
    status: str
    lang: str = ""

class ManifestRepo:
    """Minimal JSON set of processed ZIP hashes (or files) under data/state."""
    def __init__(self, path: Path | None = None):
        self.path = path or (CFG.state_dir / "zip_manifest.json")
        self._seen = set(json.loads(self.path.read_text("utf-8"))) if self.path.exists() else set()

    def seen(self, key: str) -> bool:
        return key in self._seen

    def add(self, key: str) -> None:
        self._seen.add(key)
        self.path.write_text(json.dumps(sorted(self._seen)), encoding="utf-8")

class ZipIngestor:
    ALLOWED_EXT = {".pdf",".docx",".d83",".dwg",".jpg",".png",".tiff",".zip"}
    MAX_MB = 100

    def __init__(self, manifest: ManifestRepo | None = None):
        CFG.extract_dir.mkdir(parents=True, exist_ok=True)
        CFG.logs_dir.mkdir(parents=True, exist_ok=True)
        CFG.state_dir.mkdir(parents=True, exist_ok=True)
        self.manifest = manifest or ManifestRepo()

    def _sha256(self, p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1<<20), b""):
                h.update(chunk)
        return h.hexdigest()

    def _sample_text(self, p: Path) -> str:
        try:
            if p.suffix.lower() == ".pdf":
                with fitz.open(p) as doc:
                    return (doc[0].get_text() if len(doc) else "")[:3000]
            if p.suffix.lower() == ".docx":
                d = docx.Document(p)
                return " ".join(par.text for par in d.paragraphs)[:3000]
        except Exception:
            return ""
        return ""

    def _analyse_file(self, p: Path) -> FileInfo:
        size_mb = p.stat().st_size / (1024**2)
        if p.suffix.lower() not in self.ALLOWED_EXT:
            return FileInfo(p, size_mb, "invalid_format")
        if size_mb > self.MAX_MB:
            return FileInfo(p, size_mb, "oversized")
        lang = ""
        if p.suffix.lower() in {".pdf",".docx",".txt"}:
            text = self._sample_text(p) if p.suffix.lower() in {".pdf",".docx"} else p.read_text(errors="ignore")[:3000]
            if text:
                try: lang = langdetect.detect(text)
                except Exception: lang = ""
        return FileInfo(p, size_mb, "valid", lang)

    def _log_row(self, row: list[str]) -> None:
        csv_path = CFG.logs_dir / f"ingest_{datetime.utcnow():%Y-%m}.csv"
        new = not csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new: w.writerow(["root_zip","nested_zip","file","size_mb","status","lang"])
            w.writerow(row)

    def _extract_zip(self, zip_path: Path, root_zip: Path) -> int:
        count = 0
        try:
            with zipfile.ZipFile(zip_path) as z:
                for member in z.infolist():
                    out = CFG.extract_dir / member.filename
                    if member.is_dir():
                        out.mkdir(parents=True, exist_ok=True)
                        continue
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, out.open("wb") as dst:
                        dst.write(src.read())
                    # recurse if nested zip
                    if out.suffix.lower() == ".zip":
                        count += self._extract_zip(out, root_zip)
                    else:
                        info = self._analyse_file(out)
                        self._log_row([str(root_zip.name), str(zip_path.name), str(out), f"{info.size_mb:.2f}", info.status, info.lang])
                        count += 1
        except Exception as e:
            logging.exception(f"Corrupt zip: {zip_path} :: {e}")
        return count

    def run(self) -> int:
        """Extract all zips from raw_dir into extract_dir. Returns number of files analyzed."""
        total = 0
        for zip_path in CFG.raw_dir.rglob("*.zip"):
            h = self._sha256(zip_path)
            if self.manifest.seen(h):
                logging.info(f"Skip already processed: {zip_path}")
                continue
            logging.info(f"Extracting {zip_path}")
            total += self._extract_zip(zip_path, root_zip=zip_path)
            self.manifest.add(h)
        return total

class ExcelCleaner:
    """Find latest Excel in raw_dir, clean, and write cleaned_metadata to metadata_dir."""
    def run(self) -> Path:
        exc = sorted(CFG.raw_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not exc: raise FileNotFoundError("No .xlsx in data/raw")
        src = exc[0]
        import pandas as pd
        df = pd.read_excel(src)
        df = df.dropna(how="all")
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        if "dtad_id" in df.columns:
            df["dtad_id"] = df["dtad_id"].astype(str).str.strip()
        CFG.metadata_dir.mkdir(parents=True, exist_ok=True)
        out_csv = CFG.metadata_dir / "cleaned_metadata.csv"
        out_xlsx = CFG.metadata_dir / "cleaned_metadata.xlsx"
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        df.to_excel(out_xlsx, index=False)
        logging.info(f"Cleaned metadata written: {out_csv}")
        return out_xlsx

class PDFLoader:
    """🔧 ENHANCED: PDF loader with OCR fallback for scanned documents"""
    def __init__(self, use_ocr: bool = True):
        self.use_ocr = use_ocr
        self.ocr_stats = {"attempted": 0, "successful": 0, "failed": 0}
        
    def load_pages(self, pdf_path: Path) -> List[DocumentPage]:
        """Load pages with OCR fallback for scanned documents"""
        pages: List[DocumentPage] = []
        
        try:
            with fitz.open(pdf_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # Try to extract text normally first
                    text = page.get_text().strip()
                    
                    # If no meaningful text found and OCR is enabled, try OCR
                    if len(text) < 50 and self.use_ocr:  # Less than 50 chars = likely scanned
                        ocr_text = self._ocr_page(page, page_num, pdf_path.name)
                        if ocr_text:
                            text = ocr_text
                    
                    # Only add page if we got some meaningful text
                    if text and len(text.strip()) > 10:
                        pages.append(DocumentPage(
                            page_number=page_num + 1,
                            text=text,
                            source_path=pdf_path,
                            meta={
                                "loader": "pymupdf",
                                "used_ocr": len(text) > 50 and not page.get_text().strip()
                            }
                        ))
            
            return pages
            
        except Exception as e:
            logging.error(f"Error loading PDF {pdf_path}: {e}")
            return []

    def _ocr_page(self, page, page_num: int, filename: str) -> str:
        """Extract text from page using OCR"""
        self.ocr_stats["attempted"] += 1
        
        try:
            # Convert PDF page to image with higher resolution for better OCR
            matrix = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=matrix)
            img_data = pix.tobytes("png")
            pix = None  # Free memory immediately
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(img_data))
            
            # Perform OCR with German + English language support
            text = pytesseract.image_to_string(
                image, 
                lang='deu+eng',  # German + English
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzäöüßÄÖÜ0123456789.,!?:;()-€/\\ \t\n'
            )
            
            image.close()
            
            # Clean up OCR text
            text = text.strip()
            
            # Only keep results with meaningful content
            if len(text) >= 20:  # At least 20 characters
                self.ocr_stats["successful"] += 1
                logging.info(f"📖 OCR extracted {len(text)} chars from {filename} page {page_num + 1}")
                return text
            else:
                return ""
                
        except Exception as e:
            self.ocr_stats["failed"] += 1
            logging.error(f"OCR failed on {filename} page {page_num + 1}: {e}")
            return ""

    def get_ocr_stats(self) -> Dict[str, int]:
        """Get OCR processing statistics"""
        return self.ocr_stats.copy()

class ExcelMetadataJoiner:
    """Join cleaned Excel metadata onto payloads by dtad_id or filename stem."""
    def __init__(self, cleaned_path: Path | None = None):
        self.cleaned_path = Path(cleaned_path) if cleaned_path else (CFG.metadata_dir / "cleaned_metadata.xlsx")
        self._map: dict[str, dict] = {}
        self._loaded = False

    def _load_once(self):
        if self._loaded:
            return
        self._loaded = True
        try:
            if not self.cleaned_path.exists():
                logging.warning(f"ExcelMetadataJoiner: missing {self.cleaned_path}, continuing without metadata.")
                return
            df = pd.read_excel(self.cleaned_path)
            if df.empty:
                logging.warning(f"ExcelMetadataJoiner: {self.cleaned_path} is empty, continuing without metadata.")
                return
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            if "dtad_id" in df.columns:
                df["dtad_id"] = df["dtad_id"].astype(str).str.strip()
                self._map = {
                    str(row["dtad_id"]).strip(): row.to_dict()
                    for _, row in df.iterrows()
                    if pd.notna(row.get("dtad_id", None))
                }
            else:
                logging.warning("ExcelMetadataJoiner: no 'dtad_id' column found.")
        except Exception as e:
            logging.exception(f"ExcelMetadataJoiner: failed to read {self.cleaned_path}: {e}")

    def enrich(self, path: Path, meta: dict) -> dict:
        """Attach row data if we can match by dtad_id or filename digits."""
        self._load_once()
        if not self._map:
            return meta

        # prefer explicit dtad_id in meta
        key = str(meta.get("dtad_id", "")).strip()
        if not key:
            # fallback: guess from filename digits (take first 8 if present)
            stem_digits = "".join(ch for ch in path.stem if ch.isdigit())
            key = stem_digits[:8] if len(stem_digits) >= 8 else stem_digits

        if key and key in self._map:
            merged = {**meta, **self._map[key]}
            merged["dtad_id"] = key  # ensure string
            return merged
        return meta
