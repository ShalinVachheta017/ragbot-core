#!/usr/bin/env python3
"""
Nuclear cleanup — wipe dev artifacts safely for a fresh start.

Features
- Dry-run preview (--dry-run)
- One-shot confirmation (--yes)
- Delete the current Qdrant collection (default) or all collections (--wipe-all)
- Robust Windows-safe removal of files/dirs, incl. __pycache__
- Uses core.config.CFG paths when available
"""

from __future__ import annotations
import argparse
import os
import shutil
from pathlib import Path

# Optional: use project config if present
try:
    from core.config import CFG  # type: ignore
    HAVE_CFG = True
except Exception:
    HAVE_CFG = False


# ---------- helpers ----------

def _on_rm_error(func, path, exc_info):
    """Windows-safe removal of read-only files."""
    try:
        os.chmod(path, 0o666)
        func(path)
    except Exception:
        pass

def rm_file(p: Path, dry: bool):
    if p.exists():
        print(f"  ❌ file: {p}")
        if not dry:
            p.unlink(missing_ok=True)

def rm_tree(p: Path, dry: bool):
    if p.exists():
        print(f"  🗑️  dir : {p}")
        if not dry:
            shutil.rmtree(p, onerror=_on_rm_error)

def rm_glob(root: Path, pattern: str, dry: bool):
    for fp in root.glob(pattern):
        if fp.is_file():
            rm_file(fp, dry)
        elif fp.is_dir():
            rm_tree(fp, dry)


# ---------- qdrant ops ----------

def delete_qdrant_collection(collection: str | None, wipe_all: bool, dry: bool) -> bool:
    try:
        from qdrant_client import QdrantClient  # lazy import
    except Exception:
        print("⚠️  qdrant_client not installed — skipping Qdrant deletion.")
        return False

    # Determine URL
    qdrant_url = CFG.qdrant_url if HAVE_CFG else "http://127.0.0.1:6333"
    client = QdrantClient(url=qdrant_url)

    try:
        cols = client.get_collections().collections
        names = [c.name for c in cols]
    except Exception as e:
        print(f"❌ Could not query Qdrant collections at {qdrant_url}: {e}")
        return False

    if wipe_all:
        if not names:
            print("ℹ️  Qdrant has no collections.")
            return False
        print(f"🗑️  Deleting ALL collections: {names}")
        if dry:
            return True
        ok = True
        for name in names:
            try:
                client.delete_collection(name)
                print(f"   ✅ {name}")
            except Exception as e:
                ok = False
                print(f"   ❌ {name}: {e}")
        return ok

    coll = collection or (CFG.qdrant_collection if HAVE_CFG else None)
    if not coll:
        print("ℹ️  No collection specified and CFG not available — skipping deletion.")
        return False

    if coll not in names:
        print(f"ℹ️  No collection named '{coll}' found.")
        return False

    print(f"🗑️  Deleting collection: {coll}")
    if dry:
        return True

    try:
        client.delete_collection(coll)
        print("   ✅ deleted")
        return True
    except Exception as e:
        print(f"   ❌ failed: {e}")
        return False


# ---------- main workflow ----------

def cleanup_scripts_and_ui(project_root: Path, dry: bool):
    print("🧹 Cleaning scripts and UI…")

    scripts_dir = project_root / "scripts"
    ui_dir      = project_root / "ui"

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
    for name in unwanted_scripts:
        rm_file(scripts_dir / name, dry)

    unwanted_ui_patterns = [
        "debug_*.py",
        "pytorch_*.py",
        "working_*.py",
        "clean_*.py",
        "simple_*.py",
        "minimal_*.py",
        "test_*.py",
        "__pycache__",
    ]
    for pat in unwanted_ui_patterns:
        rm_glob(ui_dir, pat, dry)

    # remove stray __pycache__ in scripts too
    rm_glob(scripts_dir, "__pycache__", dry)


def cleanup_data_dirs(project_root: Path, dry: bool):
    print("\n🗑️  Cleaning data/log directories…")

    if HAVE_CFG:
        # Prefer configured locations
        targets = {
            "logs_dir": CFG.logs_dir,
            "state_dir": getattr(CFG, "state_dir", project_root / "data" / "state"),
            "runs_dir": project_root / "data" / "runs",
            "legacy_logs": project_root / "logs",
        }
        for label, p in targets.items():
            rm_tree(Path(p), dry)
        # Recreate essentials
        essentials = [getattr(CFG, "extract_dir", project_root / "data" / "extract"),
                      CFG.logs_dir]
        for p in essentials:
            print(f"  📁 ensure: {Path(p)}")
            if not dry:
                Path(p).mkdir(parents=True, exist_ok=True)
    else:
        # Fallback to hardcoded layout
        for p in [project_root / "data" / "logs",
                  project_root / "data" / "runs",
                  project_root / "data" / "state",
                  project_root / "logs"]:
            rm_tree(p, dry)
        for p in [project_root / "data" / "extract",
                  project_root / "data" / "logs",
                  project_root / "logs"]:
            print(f"  📁 ensure: {p}")
            if not dry:
                p.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Nuclear cleanup for the RAG workspace.")
    parser.add_argument("--yes", action="store_true", help="Do not prompt for confirmation.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted, but do nothing.")
    parser.add_argument("--wipe-all", action="store_true", help="Delete ALL Qdrant collections.")
    parser.add_argument("--collection", type=str, default=None, help="Specific Qdrant collection to delete.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    print("🚀 Nuclear Cleanup")
    print("=" * 60)
    print(f"root: {project_root}")
    print(f"dry : {args.dry_run} | wipe_all: {args.wipe_all} | collection: {args.collection}")

    if not args.yes and not args.dry_run:
        ans = input("⚠️  This will delete files and Qdrant data. Continue? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            print("↩️  Aborted.")
            return

    # 1) files
    cleanup_scripts_and_ui(project_root, args.dry_run)

    # 2) qdrant
    print("\n🗑️  Qdrant collections…")
    q_ok = delete_qdrant_collection(args.collection, args.wipe_all, args.dry_run)

    # 3) data dirs
    cleanup_data_dirs(project_root, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("🎉 Cleanup complete.")
    print(f"{'✅' if q_ok else 'ℹ️'} Qdrant collections {'deleted' if q_ok else 'unchanged'}")
    if args.dry_run:
        print("🧪 Dry-run mode: no changes were made.")

if __name__ == "__main__":
    main()
