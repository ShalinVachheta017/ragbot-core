
# 📚Local Multilingual RAGbot

**RAGbot** is a Retrieval-Augmented Generation (RAG) system built to process and analyze **German public tender documents** (Vergabeunterlagen) with multilingual support.
It enables users to query unstructured procurement data and receive **structured, explainable, source-cited answers** in an intuitive UI.

This project runs **fully offline** on your local machine using **Qdrant** (vector DB), **LangChain** pipeline, **cross-encoder reranking**, and **LLMs via Ollama**.

---

## ✨ Key Features

* 🔎 **Multilingual RAG Pipeline** (German + English, scalable to other languages)
* 📑 **Rich document support**: PDF, Excel, DOCX, scanned files (OCR-ready)
* ⚡ **GPU-accelerated embeddings** (E5-small, BGE, etc.)
* 🗄️ **Qdrant Vector DB** for fast and persistent semantic search
* 🧠 **Reranking** with cross-encoders (ms-marco, BGE) for improved relevance
* 🤖 **Answer generation via Ollama** (Qwen2.5, Llama, Mistral etc.)
* 📊 **Structured responses**: answers + categories + cited sources
* 🖥️ **Streamlit UI** with sidebar controls (filters, top-k, model selection)
* 🔒 **Privacy-first**: everything runs locally (no external API calls)

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    A[📄 Tender Docs (PDF, Excel, Word, OCR)] --> B[🧹 Parser & Metadata Cleaner]
    B --> C[✂️ Chunking + GPU Embeddings]
    C --> D[(🗄️ Qdrant Vector DB)]
    D --> E[🔎 Retriever (Top-K Search)]
    E --> F[🤖 Cross-Encoder Reranker]
    F --> G[🧠 LLM via Ollama]
    G --> H[📝 Answer Generator]
    H --> I[💻 Streamlit UI]

    subgraph User
        Q[❓ User Query]
        R[📑 Structured Answer + Sources]
    end

    Q --> E
    I --> R
```

---

## 🚀 Quickstart

### 1️⃣ Clone repo & install requirements

```bash
git clone https://github.com/ShalinVachheta017/ragbot-core.git
cd ragbot-core
pip install -r requirements.txt
```

### 2️⃣ Start Qdrant with Docker

```bash
docker compose up -d
```

### 3️⃣ Ingest documents

```bash
python scripts/parse_excel.py
python scripts/embed_chunks_qdrant.py
```

### 4️⃣ Run Streamlit app

```bash
streamlit run scripts/app_streamlit.py
```

---

## 🖥️ UI Preview

* Query tender docs with natural language (DE/EN)
* Filter by metadata (e.g. CPV codes, filenames)
* Adjust `Top-K results` & reranker candidates
* Answers include **citations + categories + summaries**

---

## 📂 Project Structure

```
scripts/
 ├── app_streamlit.py       # Streamlit UI
 ├── rag_qdrant.py          # Qdrant RAG pipeline + reranker
 ├── embed_chunks_qdrant.py # Chunking + embeddings → Qdrant
 ├── parse_excel.py         # Parse + clean tender metadata
 ├── config.py              # Central config (paths, models)
 └── tools/ensure_qdrant.py # Helper for Qdrant readiness
metadata/                   # Cleaned metadata, logs, embeddings
docker-compose.yml          # Qdrant service orchestration
requirements.txt            # Python dependencies
```

---

## 🔮 Future Work & Roadmap

* 📷 **Multimodal RAG**: support for images (e.g. construction site drawings, blueprints)
* 📈 **Analytics Dashboard** (Streamlit / Power BI) for tender insights
* 🌐 **Web deployment** (FastAPI backend + Streamlit/Next.js frontend)
* 📊 **Advanced filters**: CPV hierarchy, region/state queries
* 🧩 **Plug-in connectors** for APIs (OpenWebUI, SharePoint, Tender portals)
* 🔎 **Agentic RAG**: reasoning chains & multi-hop document queries
* 🛠️ **Enterprise readiness**: RBAC, audit logs, encrypted storage

---

## 📜 License

MIT License – free to use & adapt with attribution.

---

