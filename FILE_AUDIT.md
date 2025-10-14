# 🔍 Project File Audit & Cleanup Plan

**Date:** October 14, 2025  
**Purpose:** Identify essential vs. deletable files before starting core improvements

---

## ✅ ESSENTIAL FILES (Keep)

### Core Application
- **core/** - Main RAG logic
  - ✅ `config.py` - Configuration management (Pydantic settings)
  - ✅ `search.py` - Dense vector search (Qdrant + Jina embeddings)
  - ✅ `qa.py` - Q&A pipeline (retrieval + LLM generation)
  - ✅ `domain.py` - Data models (Pydantic classes)
  - ✅ `io.py` - File I/O utilities
  - ✅ `logger.py` - Logging setup
  - ❓ `comprehensive_logger.py` - **CHECK IF USED** (might be duplicate)
  - ❓ `index.py` - **CHECK IF USED** (indexing logic)

### UI & Scripts
- **ui/**
  - ✅ `app_streamlit.py` - **ACTIVE UI** (only one being used)
  - ❌ `tender_bot_ui.py` - **DELETE** (old version, not used)
  - ❌ `multilingual_tender_bot.py` - **DELETE** (old version, not used)

- **scripts/** - Data processing pipelines
  - ✅ `embed.py` - Document embedding pipeline (KEEP - used for indexing)
  - ✅ `parse_excel.py` - Metadata parser (KEEP - used for metadata)
  - ✅ `ingest.py` - Document ingestion (KEEP - might be used)
  - ✅ `search.py` - Search utilities (KEEP - CLI search tool)
  - ❓ `direct_embedding_pipeline.py` - **CHECK IF DUPLICATE OF embed.py**
  - ❓ `unified_document_processor.py` - **CHECK IF DUPLICATE OF ingest.py**
  - ❌ `nuclear_cleanup.py` - **DELETE** (one-time cleanup, no longer needed)
  - ❌ `__init__.py` - **DELETE** (scripts not a package)

### Configuration & Documentation
- ✅ `pyproject.toml` - Python project config (KEEP)
- ✅ `requirements.txt` - Dependencies (KEEP)
- ✅ `docker-compose.yml` - Qdrant service (KEEP)
- ✅ `.gitignore` - Git ignore rules (KEEP)
- ✅ `README.md` - Main documentation (KEEP)
- ✅ `QUICKSTART.md` - Quick start guide (KEEP)
- ✅ `PRODUCTION_GUIDE.md` - Production guide (KEEP)
- ✅ `INTERVIEW_PREP_GUIDE.md` - Interview prep (KEEP - useful reference)
- ✅ `LICENSE` - MIT license (KEEP)
- ✅ `diagram.png` - Architecture diagram (KEEP - used in README)
- ✅ `deploy_production.py` - Deployment script (KEEP)

### Documentation
- **docs/** - Additional docs
  - ✅ All markdown files (KEEP - good documentation)

---

## ❌ FILES TO DELETE (Not Contributing to Project)

### Root Directory Clutter
1. **`test.py`** - Just random testing snippets (Jupyter-style cells)
   - Contains: Jina embeddings tests, OCRmyPDF checks, metadata analysis
   - **Reason:** Not part of main application, just ad-hoc testing
   - **Action:** DELETE (or move useful parts to proper test suite)

2. **`rag_qdrant.py`** - Thin adapter wrapper over core.qa
   - Contains: Simple wrapper with `search()` function
   - **Reason:** Unnecessary abstraction layer, UI calls core.qa directly
   - **Action:** DELETE

3. **`config.py`** (root) - **DUPLICATE** of `core/config.py`
   - **Reason:** Same content as core/config.py, causes confusion
   - **Action:** DELETE (keep only core/config.py)

4. **`update.ipynb`** - Temporary Jupyter notebook
   - **Reason:** Development artifact, not part of production
   - **Action:** DELETE

5. **`notes.txt`** - Random notes file
   - **Reason:** Not structured documentation
   - **Action:** DELETE (move important notes to docs/)

6. **`=1.2.10`** and **`=20.0`** - Mystery files (likely pip install artifacts)
   - **Reason:** Not supposed to be in project
   - **Action:** DELETE

7. **`env_venv_backup.yml`** - Old conda environment backup
   - **Reason:** requirements.txt is the source of truth
   - **Action:** DELETE

### UI Directory
8. **`ui/tender_bot_ui.py`** - Old UI version
   - **Reason:** `app_streamlit.py` is the active UI
   - **Action:** DELETE

9. **`ui/multilingual_tender_bot.py`** - Another old UI version
   - **Reason:** `app_streamlit.py` is the active UI
   - **Action:** DELETE

### Scripts Directory
10. **`scripts/nuclear_cleanup.py`** - One-time cleanup script
    - **Reason:** Already executed, no longer needed
    - **Action:** DELETE

11. **`scripts/__init__.py`** - Makes scripts a package
    - **Reason:** Scripts are CLI tools, not imported as package
    - **Action:** DELETE

12. **`scripts/direct_embedding_pipeline.py`** - **CHECK FIRST**
    - **Reason:** Might be duplicate of embed.py
    - **Action:** Compare with embed.py, delete if duplicate

13. **`scripts/unified_document_processor.py`** - **CHECK FIRST**
    - **Reason:** Might be duplicate of ingest.py
    - **Action:** Compare with ingest.py, delete if duplicate

### Core Directory (Check)
14. **`core/comprehensive_logger.py`** - **CHECK IF USED**
    - **Reason:** Might be duplicate of logger.py
    - **Action:** Grep for imports, delete if not used

### Build Artifacts (Cleanable)
15. **`__pycache__/`** - Python bytecode cache
    - **Action:** DELETE (regenerates automatically)

16. **`multilingual_ragbot.egg-info/`** - Build metadata
    - **Action:** DELETE (regenerates on `pip install -e .`)

17. **`qdrant_storage/`** and **`qdrant_storage;C/`** - Local Qdrant data
    - **Action:** KEEP (contains indexed vectors, but not tracked in git)

18. **`logs/`** - Application logs
    - **Action:** KEEP directory (but not tracked in git)

19. **`.qodo/`** - Qodo/Codium AI artifacts
    - **Action:** DELETE or keep (IDE-specific, should be in .gitignore)

---

## 📋 CLEANUP CHECKLIST

### Phase 1: Safe Deletions (No Impact)
- [ ] Delete `test.py`
- [ ] Delete `rag_qdrant.py`
- [ ] Delete `update.ipynb`
- [ ] Delete `notes.txt`
- [ ] Delete `=1.2.10` and `=20.0`
- [ ] Delete `env_venv_backup.yml`
- [ ] Delete `ui/tender_bot_ui.py`
- [ ] Delete `ui/multilingual_tender_bot.py`
- [ ] Delete `scripts/nuclear_cleanup.py`
- [ ] Delete `scripts/__init__.py`

### Phase 2: Verify Before Deletion
- [ ] Check if `config.py` (root) is used anywhere → Delete if not
- [ ] Check if `core/comprehensive_logger.py` is used → Delete if not
- [ ] Check if `core/index.py` is used → Keep or delete
- [ ] Compare `scripts/direct_embedding_pipeline.py` vs `embed.py` → Delete duplicate
- [ ] Compare `scripts/unified_document_processor.py` vs `ingest.py` → Delete duplicate

### Phase 3: Build Artifact Cleanup
- [ ] Delete `__pycache__/` directories (will regenerate)
- [ ] Delete `multilingual_ragbot.egg-info/` (will regenerate)
- [ ] Add `.qodo/` to `.gitignore` if not already there

---

## 📊 ESTIMATED IMPACT

**Before Cleanup:**
- ~46 Python files
- Multiple duplicate/unused files
- Confusing structure

**After Cleanup:**
- ~30-35 essential Python files
- Clear separation: core/, ui/, scripts/
- Reduced confusion

**Benefits:**
- ✅ Cleaner codebase
- ✅ Easier navigation
- ✅ Faster development
- ✅ Better onboarding for new contributors

---

## 🚀 NEXT STEPS AFTER CLEANUP

Once cleanup is complete, proceed with core improvements:

1. **Hybrid Search (Dense + BM25)** - Add keyword search
2. **Cross-Encoder Reranker** - Improve result relevance
3. **Evaluation Framework** - Automated testing & metrics
4. **Monitoring Dashboard** - Track performance & errors

**See TODO list for detailed implementation steps!**
