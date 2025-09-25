# core/parse_excel.py
from __future__ import annotations

"""
VergabeNerd Excel Parser - Metadata Cleaning & Export

Purpose:
    - Processes Excel files containing metadata
    - Performs data cleaning and standardization
    - Exports results in both CSV and XLSX formats
    - Maintains detailed logging of the process

Flow:
    1. Locates the most recent Excel file in raw data directory (if no CLI path given)
    2. Loads and cleans the data
    3. Exports cleaned data in multiple formats
"""

from pathlib import Path
import logging
import sys
import time
from typing import Optional

import pandas as pd

from .config import CFG

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_FILE = CFG.logs_dir / "parse_excel.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Configure file logger
logging.basicConfig(
    filename=str(LOG_FILE),
    filemode="w",
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    encoding="utf-8",
)
# Add console handler
_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger("").addHandler(_console)
logger = logging.getLogger("parse_excel")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _list_excel_files(root: Path) -> list[Path]:
    # Ignore temporary Excel files like "~$file.xlsx"
    return [p for p in root.rglob("*.xlsx") if not p.name.startswith("~$")]


def find_latest_excel(raw_dir: Path) -> Optional[Path]:
    """
    Find the most recent Excel file in the raw data directory.
    """
    files = _list_excel_files(raw_dir)
    if not files:
        logger.error(f"❌ No Excel files found in {raw_dir}")
        return None
    latest = max(files, key=lambda f: f.stat().st_mtime)
    logger.info(f"✅ Latest Excel: {latest}")
    return latest


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Strip whitespace
    - Replace spaces/hyphens with underscores
    - Lowercase column names
    """
    df = df.copy()
    df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]
    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Best-effort typing for common fields:
      - datum/date -> datetime (kept as original column, with 'year' derived)
      - dtad_id -> zero-padded string (8 chars) if it looks numeric
      - region -> string trimmed & lower-cased
    """
    df = df.copy()

    # date/datum -> datetime + year
    for col in ("datum", "date"):
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                if "year" not in df.columns:
                    df["year"] = df[col].dt.year
            except Exception:
                pass

    # dtad_id -> string (keep leading zeros)
    if "dtad_id" in df.columns:
        def _fmt(v):
            try:
                # if numeric-like, pad to 8; else keep as string
                if pd.notna(v) and str(v).strip().isdigit():
                    return f"{int(float(v)):08d}"
                return str(v).strip()
            except Exception:
                return str(v)
        df["dtad_id"] = df["dtad_id"].apply(_fmt)

    # region -> normalized string
    if "region" in df.columns:
        df["region"] = df["region"].apply(lambda x: str(x).strip().lower() if pd.notna(x) else x)

    return df


def clean_excel(path: Path) -> Optional[pd.DataFrame]:
    """
    Load and clean the metadata Excel file.
    Steps:
      1) Read
      2) Drop completely empty rows
      3) Normalize column names
      4) Fill NaNs with empty string (safe for UI filters)
      5) Best-effort type coercions (date/year/dtad_id/region)
    """
    try:
        logger.info(f"📥 Loading Excel: {path}")
        df = pd.read_excel(path)  # engine auto-detected
        logger.info(f"📊 Loaded {len(df)} rows, {len(df.columns)} columns")

        logger.info(f"🧾 Columns (raw): {list(df.columns)}")

        # Basic cleaning
        df.dropna(how="all", inplace=True)
        df = normalize_columns(df)
        df.fillna("", inplace=True)

        # Coerce common types
        df = coerce_types(df)

        logger.info(f"🧾 Columns (normalized): {list(df.columns)}")
        logger.info(f"📊 Final rows: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"❌ Error while reading/cleaning Excel: {e}")
        return None


def save_cleaned(df: pd.DataFrame) -> tuple[Path, Path]:
    """
    Save the cleaned DataFrame as CSV and XLSX next to each other.
    The XLSX path is exactly what the UI expects: CFG.metadata_path
    """
    out_dir = CFG.metadata_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    xlsx_path = CFG.metadata_path  # e.g., metadata/cleaned_metadata.xlsx
    csv_path = xlsx_path.with_suffix(".csv")

    # CSV as UTF-8 with BOM for Excel
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    # XLSX for the UI
    df.to_excel(xlsx_path, index=False)

    logger.info("💾 Saved cleaned metadata:")
    logger.info(f"   - CSV : {csv_path}")
    logger.info(f"   - XLSX: {xlsx_path}")
    return csv_path, xlsx_path


def clean_and_save(input_excel: Path | None = None) -> Optional[Path]:
    """
    Orchestrates the pipeline:
      - If input_excel provided, use it; else pick the latest from CFG.raw_dir
      - Clean & normalize
      - Write outputs
      - Return XLSX path (UI target) or None on error
    """
    src = Path(input_excel) if input_excel else find_latest_excel(CFG.raw_dir)
    if not src:
        return None

    df = clean_excel(src)
    if df is None:
        return None

    _, xlsx = save_cleaned(df)
    return xlsx


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main() -> None:
    """
    Usage:
        python -m core.parse_excel                 # uses latest file from CFG.raw_dir
        python -m core.parse_excel path/to/file.xlsx
    """
    start = time.time()
    logger.info("🔍 Starting Excel Parsing Phase")

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    out = clean_and_save(path)

    if out:
        logger.info(f"✅ Parsing complete in {time.time() - start:.2f}s")
        print(f"✅ Cleaned metadata written to: {out}")
    else:
        logger.error("❌ Parsing failed.")
        print("❌ Parsing failed (see logs).")


if __name__ == "__main__":
    main()
