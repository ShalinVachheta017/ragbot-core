# from pathlib import Path

# pdfs = list(Path("extractdirect").rglob("*.pdf"))
# print(f"Found: {len(pdfs)} PDF files")
# for f in pdfs[:5]:
#     print(f)
from langchain_community.vectorstores import Chroma

db = Chroma(persist_directory="chroma_db")
print(f"✅ Total embedded chunks: {db._collection.count()}")
