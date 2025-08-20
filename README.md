
# 📘 ragbot-core

A **local, multilingual Retrieval-Augmented Generation (RAG) system** for tender documents.
It is fully offline, GPU-accelerated, and powered by **Qdrant** as the vector DB, **Streamlit** as the UI, and **Ollama** for LLM inference.

---

## 🚀 Features (Current Progress)

* **End-to-End RAG Pipeline**

  * ✅ Document parsing (`Excel, PDF, DOCX`)
  * ✅ Metadata cleaning + enrichment
  * ✅ Chunking + multilingual embeddings (`intfloat/multilingual-e5-small`)
  * ✅ GPU-accelerated embedding pipeline (batch optimized)
  * ✅ Vector storage with **Qdrant** (replacing Milvus)
  * ✅ FastAPI + Streamlit integrated for querying and answers

* **Reranking for Better Answers**

  * ✅ Cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`)
  * ✅ Adjustable `top_k` and rerank candidate size in Streamlit sidebar

* **Answering System**

  * ✅ Queries in **German + English**
  * ✅ Structured answers (not just snippets, but bullet points and explanation)
  * ✅ Sources attached (`[1]`, `[2]` style referencing)

* **UI (Streamlit)**

  * ✅ Sidebar controls: embeddings, reranker, top-k slider, filters
  * ✅ Answer panel: human-readable summaries with references
  * ✅ Document hitlist: expandable chunks + scores

* **Deployment**

  * ✅ Local Docker Compose setup for Qdrant & app
  * ✅ `.gitignore` & requirements cleanup

---

## 📂 Project Structure

```
ragbot-core/
│
├── scripts/
│   ├── app_streamlit.py     # Streamlit UI + integration
│   ├── rag_qdrant.py        # Core RAG logic with Qdrant + reranker
│   ├── embed_chunks_qdrant.py  # GPU-optimized chunk embedding
│   ├── parse_excel.py       # Metadata extraction & cleaning
│   ├── config.py            # Centralized settings (paths, models, chunk size, etc.)
│   └── tools/               # Helper utilities
│
├── metadata/                # Cleaned metadata + DB
├── docker-compose.yml       # Local deployment
├── requirements.txt         # Dependencies
├── README.md                # (this file)
└── test.py                  # Minimal smoke test
```

---

## 🖥️ How to Run

1. **Clone repo & install requirements**

   ```bash
   git clone https://github.com/ShalinVachheta017/ragbot-core.git
   cd ragbot-core
   pip install -r requirements.txt
   ```

2. **Start Qdrant via Docker**

   ```bash
   docker compose up -d
   ```

3. **Ingest Documents**

   ```bash
   python scripts/embed_chunks_qdrant.py
   ```

4. **Run UI**

   ```bash
   streamlit run scripts/app_streamlit.py
   ```

---

## 📊 Example Queries

* *“Liste die Zuschlagskriterien und ihre Gewichtungen.”*
* *“How many construction tenders exist in Hessen? Group by category.”*
* *“What is the submission deadline for tender XYZ?”*

→ Produces structured answers with citations + related docs.

---

## 🛠️ Tech Stack

* **Vector DB:** [Qdrant](https://qdrant.tech)
* **Embeddings:** `intfloat/multilingual-e5-small` (GPU optimized)
* **Reranker:** `ms-marco-MiniLM-L-6-v2` cross-encoder
* **LLM:** via [Ollama](https://ollama.ai) (`qwen2.5`, switchable)
* **Frontend:** Streamlit
* **Backend:** FastAPI (structured API layer, under development)
* **Orchestration:** Docker Compose

---

## 🔮 Roadmap (Future Work)

### 📌 Phase 1 – Stabilization (Current Branches)

* [ ] Improve reranker speed (switch to lighter cross-encoder if needed)
* [ ] Add fallback summarizer (LLM-based answer augmentation)
* [ ] Error handling & logging polish

### 📌 Phase 2 – Enriched Answers

* [ ] **Structured answer templates** (timeline, deadlines, categories)
* [ ] Multi-document synthesis (combine 3–5 docs into one coherent answer)
* [ ] Ranking explanations ("why this doc was retrieved")

### 📌 Phase 3 – Multimodal Support

* [ ] Image + Table extraction from PDFs (OCR + table parsing)
* [ ] Link figures/charts to text answers
* [ ] Future: integrate CV (Construction drawings analysis)

### 📌 Phase 4 – Production Ready

* [ ] FastAPI middleware (REST API for external clients)
* [ ] CI/CD with GitHub Actions + Docker Hub
* [ ] GPU monitoring + performance benchmarking
* [ ] User roles & secure access (RBAC)

### 📌 Phase 5 – Scaling Up

* [ ] Switch embeddings to larger multilingual (bge-large, mContriever)
* [ ] Evaluate **hybrid search** (BM25 + Vector) for legal-style queries
* [ ] Add **Excel/PowerBI integration** for live tender insights
* [ ] Deploy multimodal RAG for **VergabeNerd Pro** (full SaaS)

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue to discuss major changes.
For private usage, this repo is designed to run **fully offline** (no cloud dependencies).

---

## 📜 License

MIT License © 2025 – Shalin Vachheta


