# scripts/parse_excel.py
"""
VergabeNerd Excel Parser — clean + normalize tender metadata
Outputs:
  metadata/cleaned_metadata.xlsx
  metadata/cleaned_metadata.csv
Logs:
  logs/parse_excel.log
"""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import time
from typing import List, Optional
import pandas as pd
from urllib.parse import urlparse
import re

# ---------- Logging ----------
LOG_DIR = Path("logs"); LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "parse_excel.log"

logger = logging.getLogger("parse_excel")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=7, encoding="utf-8")
    fh.setFormatter(fmt); fh.setLevel(logging.INFO)
    ch = logging.StreamHandler(); ch.setFormatter(fmt); ch.setLevel(logging.INFO)
    logger.addHandler(fh); logger.addHandler(ch)

OUTPUT_DIR = Path("metadata"); OUTPUT_DIR.mkdir(exist_ok=True)
EXCLUDE_NAMES = {"cleaned_metadata.xlsx", "cleaned_metadata.csv"}

def _find_candidates() -> List[Path]:
    roots = [Path("data"), Path("data/raw"), Path("metadata")]
    exts = (".xlsx", ".csv")
    out = []
    for root in roots:
        if root.exists():
            for p in root.rglob("*"):
                if p.suffix.lower() in exts and p.name not in EXCLUDE_NAMES:
                    out.append(p)
    return out

def find_latest_excel() -> Optional[Path]:
    cands = _find_candidates()
    if not cands:
        logger.error("No Excel/CSV files found under data/ or data/raw/. Put your source there.")
        return None
    cands.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    latest = cands[0]
    logger.info("Using source: %s (size=%d bytes)", latest, latest.stat().st_size)
    return latest

def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path, engine="openpyxl")

def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    lower = {c.lower(): c for c in df.columns}
    df.attrs["_lower_to_orig"] = lower
    return df

def _get(df: pd.DataFrame, keys):
    lower = df.attrs.get("_lower_to_orig", {})
    for k in keys:
        if k in lower:
            return lower[k]
    for k in lower:
        for target in keys:
            if target in k:
                return lower[k]
    return None

def _filename_from_url(u: str) -> Optional[str]:
    try:
        path = urlparse(str(u)).path
        name = Path(path).name
        return name or None
    except Exception:
        return None

def _cleanup_filename(v) -> Optional[str]:
    if pd.isna(v): return None
    s = str(v).strip()
    if not s: return None
    s = Path(s).name
    if "." not in s and len(s) > 3:
        s = s + ".pdf"
    return s

def clean_excel(path: Path) -> pd.DataFrame:
    df = _read_any(path)
    if df is None or df.empty:
        raise ValueError("Empty excel")

    df = _norm_cols(df)

    fname_col = _get(df, ["filename","file","pdf","datei","dokument","file_name","document"])
    url_col   = _get(df, ["url","download","link"])
    cpv_col   = _get(df, ["cpv","cpv_code","main_cpv"])
    buyer_col = _get(df, ["buyer","buyer_name","auftraggeber","agency","procuring","auftraggebername"])
    date_col  = _get(df, ["publish_date","veröffentlichungsdatum","date","datum"])
    proc_col  = _get(df, ["procedure","verfahren","verfahrensart"])
    title_col = _get(df, ["title","titel","tender_title","notice_title","bezeichnung"])

    out = pd.DataFrame()

    if fname_col and fname_col in df.columns:
        out["filename"] = df[fname_col].map(_cleanup_filename)
    else:
        fn = df[url_col].map(_filename_from_url) if url_col and url_col in df.columns else None
        out["filename"] = fn

    if out["filename"].isna().all() and title_col and title_col in df.columns:
        def slug(v):
            if pd.isna(v): return None
            s = str(v)
            s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
            return (s[:120] + ".pdf") if s else None
        out["filename"] = df[title_col].map(slug)

    out["cpv"] = df[cpv_col].astype(str).str.extract(r"([0-9]{4,}[-]?[0-9]*)", expand=False) if cpv_col and cpv_col in df.columns else None
    out["buyer"] = df[buyer_col].astype(str).str.strip() if buyer_col and buyer_col in df.columns else None
    out["published_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date.astype(str) if date_col and date_col in df.columns else None
    out["procedure"] = df[proc_col].astype(str).str.strip() if proc_col and proc_col in df.columns else None
    out["url"] = df[url_col].astype(str) if url_col and url_col in df.columns else None

    out["filename"] = out["filename"].map(lambda x: Path(str(x)).name if x else None)
    out = out.dropna(subset=["filename"]).drop_duplicates(subset=["filename"]).sort_values("filename").reset_index(drop=True)

    logger.info("Cleaned rows: %d (columns: %s)", len(out), list(out.columns))
    return out

def save_cleaned(df: pd.DataFrame) -> None:
    xlsx = OUTPUT_DIR / "cleaned_metadata.xlsx"
    csv  = OUTPUT_DIR / "cleaned_metadata.csv"
    df.to_excel(xlsx, index=False)
    df.to_csv(csv, index=False, encoding="utf-8")
    logger.info("Saved: %s & %s", xlsx, csv)

def main():
    start = time.time()
    src = find_latest_excel()
    if not src: return
    df = clean_excel(src)
    save_cleaned(df)
    logger.info("✅ Done in %.2fs", time.time()-start)

if __name__ == "__main__":
    main()
