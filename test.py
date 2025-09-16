#%%
##!/usr/bin/env python3
"""
Nuclear cleanup - removes ALL unwanted files an```ollections for fresh start
"""

import sh```l
from pathlib import Path
import os```ef cleanup_scripts_and_ui():
    """Clean unw```ed files from scripts and UI directories"""
    
    project```ot = Path(__file__).parent.parent
    
    #```wanted script files to remove
    unwanted_scripts =``` [
        "debug_tender_bot.py",
        "pytorch_fix_chat.py", 
        "working_chat.py",
        "clean_tender_bot.py",
        "simple_fresh_pipeline.py",
        "test.py",
        "working_pipeline.py",
        "check_existing.py"
    ]
    
    #```wanted UI files (patterns)
    unwanted_ui_```terns = [
        "debug_*.py",
        "pytorch_*.py", 
        "working_*.py",
        "clean_*.py",
        "simple_*.py",
        "minimal_*.py",
        "test_*.py"
    ]
    
    print``` Cleaning scripts directory```")
    scripts_dir = project_root / "```ipts"
    removed_```nt = 0
    
    for```ript_name in unwanted_scripts:```      script_path = scripts_dir / script_name
        if script```th.exists():
            script```th.unlink()
            ```nt(f"  ❌ Removed: {```ipt_name}")
            removed_count += 1
    
    ```nt(f"\n🧹 Cleaning UI directory...")
    ui_dir```project_root / "ui"```  
    for pattern in unwanted_ui_patterns:```      for file_path in ui_dir.glob(```tern):
            if file_path```ists():
                file_path```link()
                print(f"  ❌```moved: {file_path.name}")
                ```oved_count += 1
    ```  # Remove cache```rectories
    for cache_dir in [scripts_dir / "__pycache__", ui_dir / "__pycache__"]:
        if cache_dir.exists```
            shutil.rmtree(cache_dir)
            ```nt(f"  ❌ Removed: {cache_dir```lative_to(project_root)}")```          removed_count += 1
    ```  print(f"✅ Removed {removed_count```nwanted files/directories")```ef delete_qdrant_collection():
    """Delete```isting Qdrant collection"""```  
    try:
        from```rant_client import Q```ntClient
        from core.config import CF```       
        print("\n🗑️ Connecting to Qdrant...")
        ```ent = QdrantClient(url=CFG.```ant_url)
        ```      collections = client.get_collections().```lections
        collection_names = [c.name for c in collections]
        
        if CF```drant_collection in collection_names:
            print(```️ Deleting collection```CFG.qdrant_collection}")
            client.delete```llection(CFG.qdrant_collection)
            print("```drant collection deleted successfully")
            ```urn True
        else:
            print(f"```No collection named '{CFG.qdrant_collection```found")
            return False
            
    except Import```or:
        print("⚠️ ```ant_client not available - install with: pip install qdrant-```ent")
        return False
    except Exception as e:
        print```❌ Could not delete Qdrant collection:```}")
        return False

def cleanup```ta_directories():
    """Clean data```rectories for fresh start"""
    
    project```ot = Path(__file__).parent.parent
    
    #```rectories to clean (but preserve structure)
    cleanup```rs = [
        "data/logs", 
        "data/runs",
        "data/state",
        "logs"
    ]
    
    print```n🗑️ Cleaning data directories...")
    
    for dir_name``` cleanup_dirs:
        dir```th = project_root / dir```me
        if dir_path```ists():
            shutil.rmtree(dir_```h)
            print(f"  ❌ Removed:```ir_name}")
    
    #```create essential directories
    essential_dirs = [
        "data/extract",
        "data/logs",
        "logs"
    ]
    
    for```r_name in essential_dirs:```      (project_root / dir_name).```ir(parents=True, exist_```True)
        print(``` 📁 Created: {dir_name```

def main():
    print``` Starting Nuclear Cleanup")```  print("=" * 50```   
    # Step 1: Clean files```  cleanup_scripts_and_ui()```  
    # Step 2:```lete Qdrant collection
    ```ant_deleted = delete_qdrant_collection```    
    # Step 3: Clean data directories  ```  cleanup_data_directories()```  
    # Summary```  print("\n" + "=" * 50)
    print("🎉 NUCLEAR```EANUP COMPLETE!")
    print("=" * ```
    print("✅ Unw```ed script/UI files removed")
    print("```ata directories cleaned")
    print(```'✅' if qdrant_deleted else '```} Qdrant collection {'deleted' if qdrant_delete```lse 'not found/accessible'}")
    print("\n🚀 Ready for unified document processing!")

if __name__``` "__main__":
    main()

# %%
