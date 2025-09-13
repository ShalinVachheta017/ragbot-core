"""
VergabeNerd Excel Parser - Metadata Cleaning & Export

Purpose:
    - Processes Excel files containing metadata
    - Performs data cleaning and standardization
    - Exports results in both CSV and XLSX formats
    - Maintains detailed logging of the process

Flow:
    1. Locates the most recent Excel file in raw data directory
    2. Loads and cleans the data
    3. Exports cleaned data in multiple formats
"""

import pandas as pd
import logging
from pathlib import Path
import time

# === Directory Configuration ===
# Directory containing the raw Excel files to be processed
RAW_EXCEL_DIR = Path("data/raw")
# Directory where cleaned output files will be saved
OUTPUT_DIR = Path("metadata")
OUTPUT_DIR.mkdir(exist_ok=True)

# === Logging Configuration ===
# Set up both file and console logging
LOG_FILE = Path("logs/parse_excel.log")
logging.basicConfig(
    filename=LOG_FILE,
    filemode='w',  # 'w' mode overwrites previous log file
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    encoding='utf-8'
)

# Add console output for real-time monitoring
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def find_latest_excel():
    """
    Find the most recent Excel file in the raw data directory.
    
    Returns:
        Path: Path to the latest Excel file, or None if no files found
    """
    excel_files = list(RAW_EXCEL_DIR.rglob("*.xlsx"))
    if not excel_files:
        logging.error("❌ No Excel file found in data/raw/")
        return None
    # Get the most recently modified file
    latest = max(excel_files, key=lambda f: f.stat().st_mtime)
    logging.info(f"✅ Found Excel: {latest.name}")
    return latest

def clean_excel(path):
    """
    Load and clean the metadata Excel file.
    
    Cleaning steps:
    1. Load Excel file into DataFrame
    2. Remove completely empty rows
    3. Fill missing values in text fields
    4. Clean column names by removing whitespace
    
    Args:
        path (Path): Path to the Excel file
        
    Returns:
        DataFrame: Cleaned DataFrame, or None if error occurs
    """
    try:
        logging.info("📥 Loading Excel...")
        df = pd.read_excel(path, engine='openpyxl')
        logging.info(f"📊 Loaded {len(df)} rows, {len(df.columns)} columns")

        # Log available columns for debugging
        logging.info(f"🧾 Columns: {list(df.columns)}")

        # Data cleaning steps
        df.dropna(how='all', inplace=True)  # Remove rows that are completely empty
        df.fillna('', inplace=True)  # Replace NaN with empty string in text fields
        df.rename(columns=lambda col: col.strip(), inplace=True)  # Clean column names

        return df

    except Exception as e:
        logging.error(f"❌ Error while reading Excel: {e}")
        return None

def save_cleaned(df):
    """
    Save the cleaned DataFrame in multiple formats.
    
    Saves as:
    - CSV (UTF-8 with BOM for Excel compatibility)
    - XLSX (Excel format)
    
    Args:
        df (DataFrame): Cleaned DataFrame to save
    """
    csv_path = OUTPUT_DIR / "cleaned_metadata.csv"
    xlsx_path = OUTPUT_DIR / "cleaned_metadata.xlsx"

    # Save in both formats
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')  # utf-8-sig adds BOM for Excel
    df.to_excel(xlsx_path, index=False, engine='openpyxl')

    logging.info(f"💾 Cleaned metadata saved as:")
    logging.info(f"   - CSV : {csv_path}")
    logging.info(f"   - XLSX: {xlsx_path}")

def main():
    """
    Main execution function that orchestrates the Excel parsing process.
    
    Steps:
    1. Find latest Excel file
    2. Clean the data
    3. Save results
    4. Log execution time
    """
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
