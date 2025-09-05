import os
import fitz  # PyMuPDF
import pandas as pd

def classify_document(file_path: str) -> str:
    """Classify document type: text_doc, scanned_doc, table_doc, drawing_plan"""
    try:
        doc = fitz.open(file_path)
        total_text = 0
        img_count = 0

        for page in doc:
            text = page.get_text("text")
            total_text += len(text.strip())
            img_count += len(page.get_images(full=True))

        # --- Simple rules ---
        if total_text > 500:
            return "text_doc"
        if total_text < 100 and img_count > 0:
            return "scanned_doc"
        if "Bauherr" in doc[0].get_text() or "Submission" in doc[0].get_text():
            return "table_doc"
        return "drawing_plan"

    except Exception as e:
        return f"error: {e}"

def classify_all(root_dir: str = "extractdirect", out_csv: str = "metadata/classified_docs.csv"):
    results = []
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith((".pdf", ".docx", ".doc")):
                file_path = os.path.join(root, f)
                doc_type = classify_document(file_path)
                results.append({"file": file_path, "doc_type": doc_type})
                print(f"{file_path} → {doc_type}")

    # Save results
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df = pd.DataFrame(results)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"\n✅ Classification saved to {out_csv}")
    return df

if __name__ == "__main__":
    classify_all()
