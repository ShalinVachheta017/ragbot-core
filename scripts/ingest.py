from core.io import ExcelCleaner, ZipIngestor

if __name__ == "__main__":
    # 1) Clean the newest Excel in data/raw → data/metadata/cleaned_metadata.*
    excel_path = ExcelCleaner().run()
    print(f"✅ Cleaned Excel → {excel_path}")

    # 2) Extract all ZIPs (with nested zips) from data/raw → data/extract
    files_count = ZipIngestor().run()
    print(f"✅ Ingest complete. Files analyzed/extracted: {files_count}")
