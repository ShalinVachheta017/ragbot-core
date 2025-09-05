# scripts/tools/smart_loader.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple

import fitz              # PyMuPDF
import pdfplumber
from PIL import Image
import pytesseract
from docx import Document
import extract_msg

SUPPORTED = {".pdf", ".docx", ".doc", ".msg"}
TABLE_HINTS = ("Leistungsverzeichnis", "LV", "Position", "Bieter", "Angebot",
               "Preis", "Menge", "Einheit")

# Optional: point pytesseract to your exe if not on PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def _pdf_text_pymupdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    parts = [p.get_text("text", sort=True) for p in doc]  # stable reading order
    return "\n".join(parts).strip()

def _pdf_tables_pdfplumber(pdf_path: str) -> str:
    out = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for p in pdf.pages:
                try:
                    for t in p.find_tables() or []:
                        for row in (t.extract() or []):
                            out.append("\t".join((c or "") for c in row))
                except Exception:
                    continue
    except Exception:
        pass
    return "\n".join(out)

def _pdf_ocr(pdf_path: str, lang: str = "deu") -> str:
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        parts.append(pytesseract.image_to_string(img, lang=lang))
    return "\n".join(parts).strip()

def _docx_text(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs).strip()

def _doc_text(path: str) -> str:
    # minimal: many .doc are older; consider textract/libreoffice later
    return ""

def _msg_text(path: str) -> str:
    m = extract_msg.Message(path)
    hdr = f"From: {m.sender} | To: {m.to} | Cc: {m.cc} | Date: {m.date} | Subject: {m.subject or ''}"
    return (hdr + "\n\n" + (m.body or "")).strip()

def classify_pdf_fast(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        text_len = sum(len(p.get_text("text")) for p in doc)
        img_cnt  = sum(len(p.get_images(full=True)) for p in doc)
        if text_len > 500: return "text_doc"
        if text_len < 100 and img_cnt > 0: return "scanned_doc"
        first = doc[0].get_text("text")
        if any(h in first for h in TABLE_HINTS): return "table_doc"
        return "drawing_plan"
    except Exception:
        return "error"

def load_document(path: str) -> Tuple[str, Dict]:
    ext = Path(path).suffix.lower()
    meta: Dict = {"source": path, "doc_type": "unknown", "loader_used": ""}

    if ext not in SUPPORTED:
        meta["doc_type"] = "unsupported_format"
        return "", meta

    if ext == ".pdf":
        doc_type = classify_pdf_fast(path)
        meta["doc_type"] = doc_type

        text = _pdf_text_pymupdf(path)
        used = ["pymupdf_text"]

        if doc_type in {"table_doc", "text_doc"}:
            t = _pdf_tables_pdfplumber(path)
            if t: used.append("pdfplumber_tables")
            text = ("\n".join([text, t]).strip())

        if len((text or "").strip()) < 100:
            ocr = _pdf_ocr(path, lang="deu")
            if ocr:
                used.append("tesseract_ocr")
                text = ("\n".join([text, ocr]).strip())

        meta["loader_used"] = "+".join(used)
        return text, meta

    if ext == ".docx":
        meta.update({"doc_type": "text_doc", "loader_used": "python-docx"})
        return _docx_text(path), meta

    if ext == ".doc":
        meta.update({"doc_type": "text_doc", "loader_used": "doc_fallback"})
        return _doc_text(path), meta

    if ext == ".msg":
        meta.update({"doc_type": "email", "loader_used": "extract-msg"})
        return _msg_text(path), meta

    return "", meta
