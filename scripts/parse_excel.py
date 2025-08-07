"""
VergabeNerd Excel Parser - Metadata Cleaning & Export
Reads raw Excel, cleans and enriches, saves final CSV/XLSX with logs
"""

import pandas as pd
import logging
from pathlib import Path
import time

# === Paths ===
RAW_EXCEL_DIR = Path("data/raw")
OUTPUT_DIR = Path("metadata")
OUTPUT_DIR.mkdir(exist_ok=True)

# === Logging Setup ===
LOG_FILE = Path("logs/parse_excel.log")
logging.basicConfig(
    filename=LOG_FILE,
    filemode='w',
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    encoding='utf-8'
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def find_latest_excel():
    """Find the latest Excel file in raw folder"""
    excel_files = list(RAW_EXCEL_DIR.rglob("*.xlsx"))
    if not excel_files:
        logging.error("❌ No Excel file found in data/raw/")
        return None
    latest = max(excel_files, key=lambda f: f.stat().st_mtime)
    logging.info(f"✅ Found Excel: {latest.name}")
    return latest

def clean_excel(path):
    """Load and clean metadata Excel file"""
    try:
        logging.info("📥 Loading Excel...")
        df = pd.read_excel(path, engine='openpyxl')
        logging.info(f"📊 Loaded {len(df)} rows, {len(df.columns)} columns")

        # Show available columns
        logging.info(f"🧾 Columns: {list(df.columns)}")

        # Drop empty rows
        df.dropna(how='all', inplace=True)

        # Fill missing text fields
        df.fillna('', inplace=True)

        # Optional renaming (preserve original if not needed)
        df.rename(columns=lambda col: col.strip(), inplace=True)

        return df

    except Exception as e:
        logging.error(f"❌ Error while reading Excel: {e}")
        return None

def save_cleaned(df):
    """Save cleaned Excel as CSV and XLSX"""
    csv_path = OUTPUT_DIR / "cleaned_metadata.csv"
    xlsx_path = OUTPUT_DIR / "cleaned_metadata.xlsx"

    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    df.to_excel(xlsx_path, index=False, engine='openpyxl')

    logging.info(f"💾 Cleaned metadata saved as:")
    logging.info(f"   - CSV : {csv_path}")
    logging.info(f"   - XLSX: {xlsx_path}")

def main():
    start = time.time()
    logging.info("🔍 Starting Excel Parsing Phase")
    latest_excel = find_latest_excel()

    if not latest_excel:
        return

    df = clean_excel(latest_excel)
    if df is None:
        return

    save_cleaned(df)
    logging.info(f"✅ Parsing complete in {time.time() - start:.2f}s")

if __name__ == "__main__":
    main()
