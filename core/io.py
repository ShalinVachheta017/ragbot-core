"""
Hybrid ZIP File Ingestion System

Features:
- Multi-process parallel processing of ZIP files
- SHA-256 checksums for deduplication
- Handles nested ZIP archives
- File analysis and validation
- Detailed logging and manifest tracking

File Structure:
- Source ZIPs: data/raw/
- Extracted files: extractdirect/<zip-stem>/
- Database: metadata/manifest.db (SQLite)
- Logs: metadata/ingest_log_YYYY-MM.csv (monthly rotation)
"""

import os, zipfile, hashlib, pathlib, csv, logging
from multiprocessing import Pool, Queue, cpu_count, Process
from datetime import datetime
import magic, langdetect
from tqdm import tqdm
from .manifest import seen, record        # Database operations for tracking processed files

# === Configuration Settings ===
SRC_ROOT     = pathlib.Path("data/raw")       # Source directory for ZIP files
EXTRACT_DIR  = pathlib.Path("extractdirect")  # Target directory for extracted files
CORRUPT_DIR  = pathlib.Path("_corrupt")       # Directory for corrupted ZIP files
ALLOWED_EXT  = {".pdf",".docx",".d83",".dwg",".jpg",".png",".tiff",".zip"}  # Permitted file types
MAX_MB       = 100                            # Maximum allowed file size in MB
WORKERS      = max(1, cpu_count() - 2)        # Number of parallel workers (leaves 2 cores free)

# Create necessary directories
for d in (EXTRACT_DIR, CORRUPT_DIR, pathlib.Path("logs"), pathlib.Path("metadata")):
    d.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename="logs/data_preparation.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Global queue for inter-process communication
_writer_q = None
def _init_pool(q):
    """Initialize worker process with queue reference"""
    global _writer_q
    _writer_q = q

def sha256sum(path: pathlib.Path) -> str:
    """Calculate SHA-256 hash of a file using chunked reading for memory efficiency"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):  # Read 1MB chunks
            h.update(chunk)
    return h.hexdigest()

def analyse_file(p: pathlib.Path):
    """
    Analyze a file for validity and content type
    
    Checks:
    - File extension against allowed list
    - File size against maximum limit
    - MIME type validation
    - Language detection for text-based files
    
    Returns:
        tuple: (status, language)
    """
    status, lang = "valid", ""
    ext = p.suffix.lower()
    
    # Validation checks
    if ext not in ALLOWED_EXT:
        status = "invalid_format"
    elif p.stat().st_size > MAX_MB * 1024**2:
        status = "oversized"
    else:
        try:
            mime = magic.from_file(p, mime=True)
            if not mime.startswith(("application", "image")):
                status = "corrupted"
        except Exception:
            status = "corrupted"
    
    # Language detection for text-based files
    if status == "valid" and ext in {".pdf", ".docx", ".txt"}:
        try:
            snippet = p.read_text(errors="ignore")[:3000]
            lang = langdetect.detect(snippet) if snippet else ""
        except Exception:
            pass
    return status, lang

def recurse_extract(zip_path: pathlib.Path, root_zip:str):
    """
    Recursively extract and process ZIP contents
    
    - Extracts all files from ZIP
    - Analyzes each extracted file
    - Handles nested ZIP files recursively
    - Logs extraction details to queue
    """
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir(): continue
            
            # Setup extraction path
            out_path = EXTRACT_DIR / root_zip.stem / info.filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract and analyze file
            zf.extract(info, EXTRACT_DIR / root_zip.stem)
            status, lang = analyse_file(out_path)
            
            # Log extraction details
            _writer_q.put((
                root_zip.name, zip_path.name, str(out_path),
                info.file_size, status, lang
            ))
            
            # Handle nested ZIP files
            if status == "valid" and out_path.suffix.lower() == ".zip":
                try:
                    recurse_extract(out_path, root_zip)
                except zipfile.BadZipFile:
                    logging.error("Nested corrupt: %s", out_path)

def worker(zip_path: str):
    """
    Process a single ZIP file
    
    - Calculates checksum
    - Checks for previous processing
    - Extracts contents
    - Handles corrupt files
    - Updates manifest
    """
    p = pathlib.Path(zip_path)
    h = sha256sum(p)
    if seen(h):  # Skip if already processed
        return
        
    try:
        # Count files and extract
        with zipfile.ZipFile(p) as z: total = len(z.infolist())
        recurse_extract(p, p)
        
        # Record successful processing
        record(h, {
            "filename": p.name,
            "extracted_to": str(EXTRACT_DIR / p.stem),
            "status": "success",
            "files_ok": total,
            "files_fail": 0,
            "total_files": total
        })
    except zipfile.BadZipFile:
        # Handle corrupt ZIP files
        CORRUPT_DIR.mkdir(exist_ok=True)
        p.rename(CORRUPT_DIR / p.name)
        record(h, {
            "filename": p.name, "extracted_to": "",
            "status": "corrupt", "files_ok": 0,
            "files_fail": 0, "total_files": 0
        })

def csv_writer(q: Queue):
    """
    Write extraction results to CSV
    
    - Creates monthly log files
    - Records file details and status
    - Handles queue shutdown
    """
    month_tag = datetime.utcnow().strftime("%Y-%m")
    csv_path = pathlib.Path(f"metadata/ingest_log_{month_tag}.csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["root_zip","nested_zip","file","size","status","lang"])
        while True:
            row = q.get()
            if row is None:  # Shutdown signal
                break
            w.writerow(row)

def main():
    """
    Main execution function
    
    - Finds all ZIP files
    - Sets up parallel processing
    - Manages worker processes
    - Handles progress reporting
    """
    zip_list = [str(p) for p in SRC_ROOT.rglob("*.zip")]
    logging.info("Found %d outer zips under data/raw", len(zip_list))
    
    # Setup processing queue and writer process
    q = Queue()
    writer = Process(target=csv_writer, args=(q,))
    writer.start()

    # Process ZIPs in parallel with progress bar
    with Pool(processes=WORKERS, initializer=_init_pool, initargs=(q,)) as pool:
        for _ in tqdm(pool.imap_unordered(worker, zip_list, chunksize=1),
                    total=len(zip_list), desc="Ingesting ZIPs"):
            pass
            
    # Cleanup
    q.put(None)
    writer.join()
    logging.info("Ingestion done")

if __name__ == "__main__":
    main()
