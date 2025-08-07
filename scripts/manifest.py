"""
SQLite manifest helper – SHA-256 + thread-safe
One row per OUTER zip archive.
"""

import sqlite3, pathlib, threading, time

MANIFEST_DB = pathlib.Path("metadata/manifest.db")
MANIFEST_DB.parent.mkdir(exist_ok=True)

_conn = sqlite3.connect(MANIFEST_DB, check_same_thread=False)
_conn.execute("""
CREATE TABLE IF NOT EXISTS processed (
    sha256       TEXT PRIMARY KEY,
    filename     TEXT,
    extracted_to TEXT,
    processed_at REAL,
    status       TEXT,
    files_ok     INT,
    files_fail   INT,
    total_files  INT
)
""")
_conn.commit()

_lock = threading.Lock()

def seen(sha256: str) -> bool:
    """True if this archive hash is already in the manifest."""
    with _lock:
        cur = _conn.execute("SELECT 1 FROM processed WHERE sha256=?",(sha256,))
        return cur.fetchone() is not None

def record(sha256: str, row: dict) -> None:
    """Insert / update a manifest row atomically."""
    with _lock:
        _conn.execute("""
        INSERT OR REPLACE INTO processed
        (sha256, filename, extracted_to, processed_at, status,
         files_ok, files_fail, total_files)
        VALUES (:sha256,:filename,:extracted_to,:processed_at,:status,
                :files_ok,:files_fail,:total_files)
        """, {**row, "sha256": sha256, "processed_at": time.time()})
        _conn.commit()
