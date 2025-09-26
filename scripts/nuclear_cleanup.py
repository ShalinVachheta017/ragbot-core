#!/usr/bin/env python3
"""
Nuclear cleanup - removes unwanted files, data logs, and drops the Qdrant collection for a fresh start.
"""
from __future__ import annotations

import shutil
from pathlib import Path

def cleanup_scripts_and_ui(project_root: Path):
    """Clean unwanted files from scripts and UI directories."""
    unwanted_scripts = [
        "debug_tender_bot.py",
        "pytorch_fix_chat.py",
        "working_chat.py",
        "clean_tender_bot.py",
        "simple_fresh_pipeline.py",
        "test.py",
        "working_pipeline.py",
        "check_existing.py",
    ]
    unwanted_ui_patterns = [
        "debug_*.py", "pytorch_*.py", "working_*.py", "clean_*.py",
        "simple_*.py", "minimal_*.py", "test_*.py",
    ]

    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    print("🧹 Cleaning scripts directory…")
    for name in unwanted_scripts:
        p = scripts_dir / name
        if p.exists():
            p.unlink()
            print(f"  ❌ Removed: {p.relative_to(project_root)}")

    print("🧹 Cleaning UI directory…")
    ui_dir = project_root / "ui"
    ui_dir.mkdir(exist_ok=True)
    for pattern in unwanted_ui_patterns:
        for p in ui_dir.glob(pattern):
            p.unlink()
            print(f"  ❌ Removed: {p.relative_to(project_root)}")

    for cache in [scripts_dir / "__pycache__", ui_dir / "__pycache__"]:
        if cache.exists():
            shutil.rmtree(cache)
            print(f"  ❌ Removed: {cache.relative_to(project_root)}")

def delete_qdrant_collection() -> bool:
    """Delete current Qdrant collection defined in CFG."""
    try:
        from qdrant_client import QdrantClient
        from core.config import CFG

        print("\n🗑️ Connecting to Qdrant…")
        c = QdrantClient(url=CFG.qdrant_url)
        names = [x.name for x in c.get_collections().collections]
        if CFG.qdrant_collection in names:
            print(f"🗑️ Deleting collection: {CFG.qdrant_collection}")
            c.delete_collection(CFG.qdrant_collection)
            print("✅ Qdrant collection deleted.")
            return True
        print(f"ℹ️ Collection '{CFG.qdrant_collection}' not found.")
        return False
    except Exception as e:
        print(f"❌ Could not delete Qdrant collection: {e}")
        return False

def cleanup_data_directories(project_root: Path):
    """Clean data directories for a fresh start."""
    to_wipe = ["data/logs", "data/runs", "data/state", "logs"]
    print("\n🗑️ Cleaning data directories…")
    for name in to_wipe:
        p = project_root / name
        if p.exists():
            shutil.rmtree(p)
            print(f"  ❌ Removed: {name}")

    for name in ["data/extract", "data/logs", "logs"]:
        (project_root / name).mkdir(parents=True, exist_ok=True)
        print(f"  📁 Created: {name}")

def main():
    project_root = Path(__file__).resolve().parents[1]
    print("🚀 Starting Nuclear Cleanup")
    print("=" * 50)

    cleanup_scripts_and_ui(project_root)
    dropped = delete_qdrant_collection()
    cleanup_data_directories(project_root)

    print("\n" + "=" * 50)
    print("🎉 NUCLEAR CLEANUP COMPLETE!")
    print("=" * 50)
    print("✅ Unwanted script/UI files removed")
    print("✅ Data directories cleaned")
    print(f"{'✅' if dropped else '⚠️'} Qdrant collection {'deleted' if dropped else 'not found/accessible'}")
    print("\n🚀 Ready for unified document processing!")

if __name__ == "__main__":
    main()
