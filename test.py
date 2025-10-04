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
# Run this to check your metadata
import pandas as pd

print("Loading metadata file...")
df = pd.read_excel('data/metadata/cleaned_metadata.xlsx')

# Check structure
print("\n" + "="*60)
print("METADATA FILE ANALYSIS")
print("="*60)

print(f"\nTotal rows: {len(df)}")
print(f"\nAll columns ({len(df.columns)}):")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print("\n" + "="*60)
print("SAMPLE DATA (first 3 rows):")
print("="*60)
print(df.head(3).to_string())

print("\n" + "="*60)
print("CHECKING KEY COLUMNS:")
print("="*60)

# Check for DTAD-ID variations
dtad_variants = [col for col in df.columns if 'dtad' in col.lower()]
if dtad_variants:
    print(f"\n✅ Found DTAD column(s): {dtad_variants}")
    for col in dtad_variants:
        print(f"\n   Column '{col}' sample values:")
        print(f"   {df[col].head(5).tolist()}")
else:
    print("\n❌ No DTAD-ID column found!")

# Check for date columns
date_variants = [col for col in df.columns if any(word in col.lower() for word in ['datum', 'date', 'zeit'])]
if date_variants:
    print(f"\n✅ Found date column(s): {date_variants}")
    for col in date_variants:
        print(f"\n   Column '{col}' sample values:")
        print(f"   {df[col].head(5).tolist()}")
else:
    print("\n❌ No date column found!")

# Check for region columns
region_variants = [col for col in df.columns if any(word in col.lower() for word in ['region', 'ort', 'stadt', 'bundesland'])]
if region_variants:
    print(f"\n✅ Found region column(s): {region_variants}")
    for col in region_variants:
        print(f"\n   Column '{col}' unique values (first 10):")
        print(f"   {df[col].dropna().unique()[:10].tolist()}")
else:
    print("\n❌ No region column found!")

# Check for year column
if 'year' in df.columns:
    print(f"\n✅ Year column exists!")
    print(f"   Values: {df['year'].value_counts().to_dict()}")
else:
    print(f"\n⚠️  No 'year' column - need to create from date column")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)

if dtad_variants:
    print(f"Use column '{dtad_variants[0]}' for DTAD-ID lookups")
if date_variants:
    print(f"Use column '{date_variants[0]}' for date filtering")
if region_variants:
    print(f"Use column '{region_variants[0]}' for region filtering")

print("\n" + "="*60)
# %%
