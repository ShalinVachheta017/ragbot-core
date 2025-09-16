#!/usr/bin/env python3
"""
Nuclear cleanup - removes ALL unwanted files and collections for fresh start
"""

import shutil
from pathlib import Path
import os

def cleanup_scripts_and_ui():
    """Clean unwanted files from scripts and UI directories"""
    
    project_root = Path(__file__).parent.parent
    
    # Unwanted script files to remove
    unwanted_scripts = [
        "debug_tender_bot.py",
        "pytorch_fix_chat.py", 
        "working_chat.py",
        "clean_tender_bot.py",
        "simple_fresh_pipeline.py",
        "test.py",
        "working_pipeline.py",
        "check_existing.py"
    ]
    
    # Unwanted UI files (patterns)
    unwanted_ui_patterns = [
        "debug_*.py",
        "pytorch_*.py", 
        "working_*.py",
        "clean_*.py",
        "simple_*.py",
        "minimal_*.py",
        "test_*.py"
    ]
    
    print("🧹 Cleaning scripts directory...")
    scripts_dir = project_root / "scripts"
    removed_count = 0
    
    for script_name in unwanted_scripts:
        script_path = scripts_dir / script_name
        if script_path.exists():
            script_path.unlink()
            print(f"  ❌ Removed: {script_name}")
            removed_count += 1
    
    print(f"\n🧹 Cleaning UI directory...")
    ui_dir = project_root / "ui"
    
    for pattern in unwanted_ui_patterns:
        for file_path in ui_dir.glob(pattern):
            if file_path.exists():
                file_path.unlink()
                print(f"  ❌ Removed: {file_path.name}")
                removed_count += 1
    
    # Remove cache directories
    for cache_dir in [scripts_dir / "__pycache__", ui_dir / "__pycache__"]:
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(f"  ❌ Removed: {cache_dir.relative_to(project_root)}")
            removed_count += 1
    
    print(f"✅ Removed {removed_count} unwanted files/directories")

def delete_qdrant_collection():
    """Delete existing Qdrant collection"""
    
    try:
        from qdrant_client import QdrantClient
        from core.config import CFG
        
        print("\n🗑️ Connecting to Qdrant...")
        client = QdrantClient(url=CFG.qdrant_url)
        
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if CFG.qdrant_collection in collection_names:
            print(f"🗑️ Deleting collection: {CFG.qdrant_collection}")
            client.delete_collection(CFG.qdrant_collection)
            print("✅ Qdrant collection deleted successfully")
            return True
        else:
            print(f"ℹ️ No collection named '{CFG.qdrant_collection}' found")
            return False
            
    except ImportError:
        print("⚠️ qdrant_client not available - install with: pip install qdrant-client")
        return False
    except Exception as e:
        print(f"❌ Could not delete Qdrant collection: {e}")
        return False

def cleanup_data_directories():
    """Clean data directories for fresh start"""
    
    project_root = Path(__file__).parent.parent
    
    # Directories to clean (but preserve structure)
    cleanup_dirs = [
        "data/logs", 
        "data/runs",
        "data/state",
        "logs"
    ]
    
    print("\n🗑️ Cleaning data directories...")
    
    for dir_name in cleanup_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  ❌ Removed: {dir_name}")
    
    # Recreate essential directories
    essential_dirs = [
        "data/extract",
        "data/logs",
        "logs"
    ]
    
    for dir_name in essential_dirs:
        (project_root / dir_name).mkdir(parents=True, exist_ok=True)
        print(f"  📁 Created: {dir_name}")

def main():
    print("🚀 Starting Nuclear Cleanup")
    print("=" * 50)
    
    # Step 1: Clean files
    cleanup_scripts_and_ui()
    
    # Step 2: Delete Qdrant collection
    qdrant_deleted = delete_qdrant_collection()
    
    # Step 3: Clean data directories  
    cleanup_data_directories()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 NUCLEAR CLEANUP COMPLETE!")
    print("=" * 50)
    print("✅ Unwanted script/UI files removed")
    print("✅ Data directories cleaned")
    print(f"{'✅' if qdrant_deleted else '⚠️'} Qdrant collection {'deleted' if qdrant_deleted else 'not found/accessible'}")
    print("\n🚀 Ready for unified document processing!")

if __name__ == "__main__":
    main()
