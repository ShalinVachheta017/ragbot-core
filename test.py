#%%
# 1) Jina v3 loads and embeds

from sentence_transformers import SentenceTransformer
m = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)
e = m.encode("hello", normalize_embeddings=True)
print("dim:", len(e), "sample:", e[:5])


# 2) Qdrant client import

from qdrant_client import QdrantClient
c = QdrantClient(url="http://127.0.0.1:6333")
print("qdrant ok")

# 3) OCRmyPDF presence (it will still need Ghostscript + qpdf system tools)

import shutil
print("ocrmypdf:", shutil.which("ocrmypdf"))
print("tesseract:", shutil.which("tesseract"))


# %%
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)
e = m.encode("hello", normalize_embeddings=True)
print("dim:", len(e), "sample:", e[:5])

# %%
from huggingface_hub import HfApi
print(HfApi().model_info("jinaai/jina-embeddings-v3").sha)
# %%
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("jinaai/jina-embeddings-v3", revision="f1944de8402dcd5f2b03f822a4bc22a7f2de2eb9", trust_remote_code=True)
e = m.encode("hello", normalize_embeddings=True)
print("dim:", len(e))


# %%
import shutil
from pathlib import Path
import os

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
    
def main():
    print("🚀 Starting Nuclear Cleanup")
    print("=" * 50)
    
    
    # Step 2: Delete Qdrant collection
    qdrant_deleted = delete_qdrant_collection()
    
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

# %%
# Must point to ...\envs\mllocalag\python.exe
conda run -n mllocalag python -c "import sys; print(sys.executable)"

# Packaging + HF stack
conda run -n mllocalag python -c "import packaging, importlib.metadata as md; print(packaging.__version__, md.version('packaging'))"
conda run -n mllocalag python -c "import transformers, sentence_transformers; print(transformers.__version__, sentence_transformers.__version__)"

# CUDA present?
conda run -n mllocalag python -c "import torch; print('torch', torch.__version__, 'cuda?', torch.cuda.is_available())"

# No broken deps
conda run -n mllocalag python -m pip check
# %%
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# %% 
import pytesseract 
import PIL 
import subprocess,sys
print('pytesseract OK')
subprocess.check_call(['tesseract','--version'])

# %%
# sanity_check.py (run: python sanity_check.py)
from core.config import CFG
from core.qa import retrieve_candidates
test_qs = [
    "VOB Regelungen für Nachunternehmer",
    "Technische Spezifikationen für Straßenbau",
    "Mindestlohn Bauprojekte",
    "Submission deadline requirements 2022 NRW"
]
for q in test_qs:
    hits = retrieve_candidates(q, CFG)[:5]
    print("\nQ:", q, f"(top {len(hits)})")
    for i,h in enumerate(hits,1):
        src  = h.payload.get("source_path", "NA").split("/")[-1]
        p1   = h.payload.get("page_start") or h.payload.get("page")
        p2   = h.payload.get("page_end")
        page = f"p{p1}" if p2 in (None, p1) else f"p{p1}-{p2}"
        print(f"  {i:>2}. {h.score:.3f} | {src} | {page}")
        # quick payload health
        assert "doc_hash" in h.payload, "missing doc_hash"
        assert "chunk_idx" in h.payload, "missing chunk_idx"
print("\n✅ Sanity retrieval finished")

# %%
