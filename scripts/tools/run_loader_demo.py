from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from smart_loader import load_document

EXTS = {".pdf", ".docx", ".doc", ".msg"}

def walk_files(root: str):
    for p in Path(root).rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS:
            yield p

def main(root="extractdirect", csv="metadata/loader_report.csv",
         dump_dir="logs/text_dump", save_text=True):
    os.makedirs(Path(csv).parent, exist_ok=True)
    os.makedirs(dump_dir, exist_ok=True)

    rows = []
    for i, path in enumerate(walk_files(root), 1):
        text, meta = load_document(str(path))
        meta["text_chars"] = len(text or "")
        meta["ok"] = bool((text or "").strip())
        rows.append(meta)

        if save_text and meta["ok"]:
            rel = path.relative_to(root)
            out = Path(dump_dir, rel).with_suffix(".txt")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8", errors="ignore")

        if i % 50 == 0:
            print(f"Processed {i} files…")

    df = pd.DataFrame(rows)
    df.to_csv(csv, index=False, encoding="utf-8")
    print(f"\n✅ wrote {csv} (rows={len(df)})")
    print(df["doc_type"].value_counts(dropna=False))

if __name__ == "__main__":
    main()
