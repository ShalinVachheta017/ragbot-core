"""
Hybrid ingestion • SHA-256 • multi-process • nested-zip
Search path : data/raw/
Target      : extractdirect/<zip-stem>/
Manifest    : metadata/manifest.db (SQLite)
Per-file log: metadata/ingest_log_YYYY-MM.csv (rotated monthly)
"""

import os, zipfile, hashlib, pathlib, csv, logging
from multiprocessing import Pool, Queue, cpu_count, Process
from datetime import datetime
import magic, langdetect
from tqdm import tqdm
from manifest import seen, record        # unchanged helper

# ─── CONFIG ──────────────────────────────────────────────────────────────
SRC_ROOT     = pathlib.Path("data/raw")       # <— where your ZIP folders live
EXTRACT_DIR  = pathlib.Path("extractdirect")  # <— new folder for extracted docs
CORRUPT_DIR  = pathlib.Path("_corrupt")       # quarantine
ALLOWED_EXT  = {".pdf",".docx",".d83",".dwg",".jpg",".png",".tiff",".zip"}
MAX_MB       = 100
WORKERS      = max(1, cpu_count() - 2)
for d in (EXTRACT_DIR, CORRUPT_DIR, pathlib.Path("logs"), pathlib.Path("metadata")):
    d.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename="logs/data_preparation.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
# ─────────────────────────────────────────────────────────────────────────

# shareable queue pointer for workers (Windows-safe)
_writer_q = None
def _init_pool(q):        # called in each forked process
    global _writer_q
    _writer_q = q

def sha256sum(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def analyse_file(p: pathlib.Path):
    status, lang = "valid", ""
    ext = p.suffix.lower()
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
    if status == "valid" and ext in {".pdf", ".docx", ".txt"}:
        try:
            snippet = p.read_text(errors="ignore")[:3000]
            lang = langdetect.detect(snippet) if snippet else ""
        except Exception:
            pass
    return status, lang

def recurse_extract(zip_path: pathlib.Path, root_zip:str):
    """Depth-first extraction + per-file row push."""
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir(): continue
            out_path = EXTRACT_DIR / root_zip.stem / info.filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            zf.extract(info, EXTRACT_DIR / root_zip.stem)
            status, lang = analyse_file(out_path)
            _writer_q.put((
                root_zip.name, zip_path.name, str(out_path),
                info.file_size, status, lang
            ))
            # recurse into nested archives
            if status == "valid" and out_path.suffix.lower() == ".zip":
                try:
                    recurse_extract(out_path, root_zip)
                except zipfile.BadZipFile:
                    logging.error("Nested corrupt: %s", out_path)

def worker(zip_path: str):
    p = pathlib.Path(zip_path)
    h = sha256sum(p)
    if seen(h):
        return
    try:
        with zipfile.ZipFile(p) as z: total = len(z.infolist())
        recurse_extract(p, p)
        record(h, {
            "filename": p.name,
            "extracted_to": str(EXTRACT_DIR / p.stem),
            "status": "success",
            "files_ok": total,
            "files_fail": 0,
            "total_files": total
        })
    except zipfile.BadZipFile:
        CORRUPT_DIR.mkdir(exist_ok=True)
        p.rename(CORRUPT_DIR / p.name)
        record(h, {
            "filename": p.name, "extracted_to": "",
            "status": "corrupt", "files_ok": 0,
            "files_fail": 0, "total_files": 0
        })

def csv_writer(q: Queue):
    month_tag = datetime.utcnow().strftime("%Y-%m")
    csv_path = pathlib.Path(f"metadata/ingest_log_{month_tag}.csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["root_zip","nested_zip","file","size","status","lang"])
        while True:
            row = q.get()
            if row is None:
                break
            w.writerow(row)

def main():
    zip_list = [str(p) for p in SRC_ROOT.rglob("*.zip")]
    logging.info("Found %d outer zips under data/raw", len(zip_list))
    from tqdm import tqdm
    q = Queue()
    writer = Process(target=csv_writer, args=(q,))
    writer.start()

    with Pool(processes=WORKERS, initializer=_init_pool, initargs=(q,)) as pool:
        for _ in tqdm(pool.imap_unordered(worker, zip_list, chunksize=1),     # ← remove kwds
                    total=len(zip_list), desc="Ingesting ZIPs"):
            pass
    q.put(None)
    writer.join()
    logging.info("Ingestion done")

if __name__ == "__main__":
    main()
