
# 🧠 Production-Ready Multilingual RAG System for Tender Documents

**RAGbot** is a production-grade Retrieval-Augmented Generation (RAG) system specifically designed for **German public tender documents** (Vergabeunterlagen) with full multilingual support.

Query unstructured procurement data in **German or English** and receive **accurate, grounded, source-cited answers** through an intuitive chat interface.

This system runs **100% offline** on your local machine using:
- **Qdrant** for vector storage
- **Jina Embeddings v3** (1024-D) for semantic search  
- **Ollama** for local LLM inference (Qwen2.5, Llama, Mistral)
- **Streamlit** for the web interface

✅ **Production-Ready**: Fixed syntax errors, robust error handling, metadata integration, comprehensive documentation

---

## ✨ Key Features

### Core RAG Capabilities
* 🔎 **Multilingual Semantic Search** - Query in German or English, retrieve from both
* 📑 **Rich Document Support** - PDF, Excel, DOCX, scanned files (OCR via Tesseract)
* ⚡ **High-Performance Embeddings** - Jina v3 (1024-D) with GPU acceleration
* 🗄️ **Qdrant Vector DB** - Fast, persistent semantic search with 29,086+ chunks
* 🤖 **Local LLM Generation** - Ollama (Qwen2.5:1.5b default, supports Llama/Mistral)
* 📊 **Metadata-Aware Routing** - Direct DTAD-ID lookups, date/region filters
* 🎯 **Citation Grounding** - Every answer cites sources with [1], [2] references
* � **Privacy-First** - Everything runs locally, zero external API calls

### Production Features
* ✅ **Graceful Error Handling** - Handles missing collections, network issues
* � **Metadata Integration** - 112 tenders with normalized DTAD-ID, dates, regions  
* 🧪 **Test Suite** - Comprehensive test queries and validation scripts
* 📖 **Complete Documentation** - Quickstart, production guide, testing guide
* 🚀 **One-Command Deployment** - `deploy_production.py` script included

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

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (Conda environment recommended)
- Docker (for Qdrant)
- Ollama (for local LLMs)
- 8GB+ RAM, GPU recommended for embeddings

### 1️⃣ Clone Repository

```bash
git clone https://github.com/ShalinVachheta017/ragbot-core.git
cd ragbot-core
```

### 2️⃣ Set Up Environment

```bash
# Create conda environment
conda create -n mllocalag python=3.10
conda activate mllocalag

# Install dependencies
pip install -r requirements.txt
pip install pytesseract  # For OCR support
```

### 3️⃣ Start Qdrant Vector Database

```bash
docker compose up -d
# Verify: http://localhost:6333/dashboard
```

### 4️⃣ Install Ollama Models

```bash
# Install Ollama from https://ollama.ai
ollama pull qwen2.5:1.5b
ollama pull llama3.2:1b  # Optional alternative
```

### 5️⃣ Index Your Documents

```bash
# Parse metadata
python scripts/parse_excel.py

# Embed and index documents (takes 5-10 minutes)
python scripts/embed.py --mode fresh

# Verify indexing
curl http://localhost:6333/collections/tender_chunks
```

### 6️⃣ Launch Streamlit UI

```bash
streamlit run ui/app_streamlit.py
# Open browser: http://localhost:8501
```

**Ready!** Try queries like:
- `"Was ist DTAD-ID 20046891?"`
- `"Show me tenders from 2024"`
- `"Tenders in Dresden region"`

---

## 🖥️ UI Preview

* Query tender docs with natural language (DE/EN)
* Filter by metadata (e.g. CPV codes, filenames)
* Adjust `Top-K results` & reranker candidates
* Answers include **citations + categories + summaries**

---

## 📂 Project Structure

```
multilingual-ragbot/
├── core/                          # Core RAG components
│   ├── config.py                 # Configuration management
│   ├── qa.py                     # Q&A and retrieval logic
│   ├── search.py                 # Dense vector search
│   ├── domain.py                 # Data models
│   ├── io.py                     # File I/O utilities
│   └── logger.py                 # Logging configuration
├── ui/
│   └── app_streamlit.py          # 🖥️ Main Streamlit interface
├── scripts/
│   ├── embed.py                  # Document embedding pipeline
│   ├── ingest.py                 # Document ingestion
│   ├── parse_excel.py            # Metadata parser
│   └── search.py                 # Search utilities
├── data/
│   ├── metadata/                 # Tender metadata (cleaned_metadata.xlsx)
│   ├── extract/                  # Extracted document text
│   ├── raw/                      # Original documents
│   └── logs/                     # Processing logs
├── docs/                          # 📖 Documentation
│   ├── TESTING_GUIDE.md          # Testing procedures
│   ├── SYSTEM_REVIEW.md          # System architecture review
│   └── TEST_QUERIES.md           # Example test queries
├── QUICKSTART.md                  # ⚡ Quick start guide
├── PRODUCTION_GUIDE.md            # 🚀 Production deployment guide
├── deploy_production.py           # One-command deployment
├── docker-compose.yml             # Qdrant service configuration
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md)** - Production deployment
- **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Testing procedures
- **[docs/TEST_QUERIES.md](docs/TEST_QUERIES.md)** - Example queries

## 🎯 Example Queries

The system handles various query types:

**Direct ID Lookups:**
```
"Was ist DTAD-ID 20046891?"
"Show me tender 20047108"
```

**Temporal Queries:**
```
"Show me tenders from 2024"
"What tenders were published in March?"
```

**Geographic Filters:**
```
"Tenders in Dresden"
"Show me projects in Berlin region"
```

**Semantic Questions:**
```
"Welche Unterlagen sind für VOB-konforme Ausschreibungen erforderlich?"
"What are the technical specifications for IT projects?"
"Mindestlohn requirements in construction tenders"
```

**Metadata Routing:**
- DTAD-ID queries → Direct metadata lookup (instant)
- Date/year queries → Metadata filtering  
- Semantic queries → Vector search with context

---

## 🔮 Roadmap & Future Enhancements

### 🚧 Planned Core Improvements

**Retrieval Enhancement (High Priority)**
- � **Hybrid Search** - Combine dense (semantic) + sparse (BM25) retrieval for better accuracy
  - Implement BM25 keyword matching alongside vector search
  - Weighted fusion (e.g., 70% dense + 30% sparse)
  - Expected improvement: +15% recall, especially for exact term matches
  
- 🎯 **Reranker Integration** - Cross-encoder model to reorder retrieved chunks
  - Model: `ms-marco-MiniLM-L-6-v2` or `bge-reranker-large`
  - Two-stage pipeline: Fast retrieval (top-100) → Accurate reranking (top-8)
  - Expected improvement: +20% precision, better relevance
  
- 📊 **Query Classification** - Route queries to optimal retrieval strategy
  - Factual queries → Hybrid search
  - Semantic queries → Dense only
  - ID lookups → Metadata (already implemented ✅)

**Evaluation & Quality (High Priority)**
- 📈 **Automated Evaluation Framework**
  - Metrics: Hit Rate, MRR, Precision@k, Recall@k, NDCG
  - Faithfulness scoring (grounding check)
  - Test suite with 50+ queries across categories
  - Regression testing before deployments
  
- 🧪 **A/B Testing Infrastructure**
  - Compare retrieval strategies (dense vs hybrid vs reranked)
  - LLM model comparison (Qwen vs Llama vs Mistral)
  - Prompt engineering experiments
  - User feedback collection

**Monitoring & Observability (Medium Priority)**
- 📉 **Production Monitoring**
  - Query latency tracking (p50, p95, p99)
  - Error rate monitoring (Qdrant, Ollama, parsing)
  - Cache hit rate metrics
  - User query analytics (popular queries, failure patterns)
  
- � **Alerting System**
  - Latency threshold alerts (>5s response time)
  - Error rate spikes (>5% failures)
  - System health checks (Qdrant, Ollama availability)
  - Daily/weekly metrics reports

### 🌟 Advanced Features

**Semantic & Retrieval**
- 🧠 **Semantic Chunking** - Replace fixed-size chunks with sentence-aware splitting
  - Prevents mid-sentence cuts
  - Preserves semantic meaning
  - Library: LangChain `RecursiveCharacterTextSplitter`

- 🔗 **Graph RAG** - Build knowledge graph from tender relationships
  - Entity extraction (companies, locations, amounts)
  - Relationship mapping (tender → contractor → region)
  - Multi-hop reasoning ("Find all tenders by company X in region Y")

- � **Multilingual Query Expansion**
  - Auto-translate queries (German ↔ English ↔ French)
  - Retrieve from all languages simultaneously
  - Unified ranking across languages

**Intelligence & Automation**
- 🤖 **Agentic RAG** - Multi-step reasoning for complex queries
  - "Compare tenders 20046891 and 20046893" → Multi-document analysis
  - "What changed in Dresden tenders from 2023 to 2024?" → Temporal analysis
  - Tool use: Calculator for budget analysis, date parsing

- 💡 **Smart Summarization**
  - Tender summaries on-demand
  - Highlight key requirements, deadlines, budgets
  - Multi-document summarization (region overview, category trends)

- � **Proactive Notifications**
  - Alert when new tenders match saved criteria
  - Deadline reminders
  - Competitive intelligence (similar past tenders)

**Data & Documents**
- 📷 **Multimodal RAG** - Handle images, tables, charts
  - Vision LLM (LLaVA, GPT-4V) for images
  - Table extraction and structured parsing
  - Diagram understanding (flowcharts, blueprints, site plans)

- 📊 **Structured Data Extraction**
  - Auto-extract: budgets, deadlines, requirements, contact info
  - Store in structured DB (PostgreSQL) alongside vectors
  - Enable SQL queries + semantic search combination

- 📄 **Document Generation**
  - Generate bid responses from templates
  - Compliance checklist generation
  - Requirement matching reports

**User Experience**
- 📈 **Analytics Dashboard**
  - Tender volume trends (by region, category, time)
  - Budget analysis (average, min, max by category)
  - CPV code distribution
  - Interactive visualizations (Plotly, Streamlit charts)

- 🎨 **Enhanced UI**
  - Dark/light mode toggle
  - Export answers to PDF/Word
  - Bookmark/favorite queries
  - Collaborative features (share queries, annotations)

- 🗣️ **Voice Interface** (Experimental)
  - Speech-to-text for queries
  - Text-to-speech for answers
  - Hands-free tender review

**Integration & Deployment**
- 🌐 **API Development**
  - FastAPI REST API for programmatic access
  - WebSocket support for streaming answers
  - API key authentication
  - Rate limiting and quota management

- 🔗 **External Integrations**
  - Tender portals (TED, Bund.de, regional platforms)
  - SharePoint/OneDrive document sync
  - Email notifications (SendGrid, AWS SES)
  - Slack/Teams bot integration

- � **Production Deployment**
  - Kubernetes manifests (deployments, services, ingress)
  - Horizontal pod autoscaling (HPA)
  - CI/CD pipeline (GitHub Actions)
  - Multi-environment setup (dev, staging, prod)

**Enterprise & Security**
- 🔐 **Security Hardening**
  - User authentication (OAuth2, SSO)
  - Role-based access control (RBAC)
  - Audit logs (who queried what, when)
  - Data encryption at rest and in transit

- 🏢 **Multi-Tenancy**
  - Separate collections per organization
  - Tenant isolation
  - Custom branding per tenant

- 📦 **Backup & Disaster Recovery**
  - Automated Qdrant backups
  - Point-in-time recovery
  - Geo-redundant storage

### 📅 Implementation Timeline

**Phase 1 (Months 1-2): Core Improvements**
- ✅ Hybrid search implementation
- ✅ Reranker integration
- ✅ Basic evaluation framework
- ✅ Monitoring dashboard

**Phase 2 (Months 3-4): Quality & Scale**
- Semantic chunking
- A/B testing infrastructure
- Production alerting
- Graph RAG prototype

**Phase 3 (Months 5-6): Advanced Features**
- Agentic RAG
- Multimodal support (tables, images)
- Analytics dashboard
- API development

**Phase 4 (Months 7-9): Enterprise Ready**
- Authentication & RBAC
- Multi-tenancy
- External integrations
- Kubernetes deployment

---

## 📊 Current Limitations & Known Issues

**Retrieval:**
- ❌ No hybrid search (dense-only, misses exact keyword matches)
- ❌ No reranking (retrieved chunks not optimally ordered)
- ❌ Fixed 512-char chunks (may split important context)

**Generation:**
- ⚠️ Small LLM (1.5B params) - occasionally struggles with complex German
- ⚠️ No query decomposition (complex multi-part questions need manual breakdown)
- ⚠️ Limited citation granularity (chunk-level, not sentence-level)

**Monitoring:**
- ❌ No production metrics tracking
- ❌ No error alerting
- ❌ No user feedback loop
- ❌ No A/B testing infrastructure

**Scale:**
- ⚠️ Single-node Qdrant (no replication)
- ⚠️ No caching layer (repeated queries not optimized)
- ⚠️ GPU not utilized for LLM (CPU inference slower)

**See [INTERVIEW_PREP_GUIDE.md](INTERVIEW_PREP_GUIDE.md) for detailed discussion of limitations and solutions.**

---

## 🐛 Troubleshooting

**Qdrant Connection Error:**
```bash
# Check Qdrant is running
curl http://localhost:6333/collections
# Restart if needed
docker compose restart
```

**Empty Search Results:**
```bash
# Verify documents are indexed
curl http://localhost:6333/collections/tender_chunks
# Re-index if point_count is 0
python scripts/embed.py --mode fresh
```

**Ollama Model Not Found:**
```bash
ollama list  # Check installed models
ollama pull qwen2.5:1.5b  # Install if missing
```

**Import Errors:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

MIT License - free to use and adapt with attribution.

---

## 👤 Author

**Shalin Vachheta**  
GitHub: [@ShalinVachheta017](https://github.com/ShalinVachheta017)

---

## 🙏 Acknowledgments

- **Jina AI** - Embeddings model
- **Qdrant** - Vector database
- **Ollama** - Local LLM inference
- **Streamlit** - UI framework
- German procurement community for test data

---

**⭐ Star this repo if you find it useful!**

