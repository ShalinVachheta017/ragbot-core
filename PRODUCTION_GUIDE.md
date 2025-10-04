# Production-Grade RAG System - Setup Guide

## ✅ Current Status: OPERATIONAL

**App Running**: http://localhost:8501  
**Collection Status**: Missing (needs rebuild)  
**Metadata**: ✅ Loaded (112 rows)

---

## 🚀 Production Checklist

### Phase 1: Immediate Production Readiness ✅

- [x] **Streamlit App**: Running successfully
- [x] **Error Handling**: Graceful degradation when collection missing
- [x] **Metadata Routing**: Working (DTAD-ID, year, region filters)
- [x] **Import Order**: Fixed (set_page_config first)
- [x] **Syntax Errors**: Resolved (search.py line 156)
- [x] **Dependencies**: All installed and compatible

### Phase 2: Data Indexing (REQUIRED FOR VECTOR SEARCH) 🔄

- [ ] **Rebuild Qdrant Collection**: 29,086 documents
- [ ] **Verify Embeddings**: Jina v3, 1024-dim
- [ ] **Test Vector Search**: Semantic queries working
- [ ] **Validate Chunks**: Page-aware, proper overlap

### Phase 3: Production Optimization 🎯

- [ ] **Performance Tuning**: Response time < 3s
- [ ] **Error Logging**: Comprehensive tracking
- [ ] **Monitoring**: Health checks, metrics
- [ ] **Caching**: Session-based, embedding cache
- [ ] **Rate Limiting**: Prevent abuse

---

## 📋 Step-by-Step Production Deployment

### Step 1: Rebuild Vector Database (CRITICAL)

```bash
# Navigate to project
cd D:\Projects\multilingual-ragbot

# Activate environment
conda activate mllocalag

# Run indexing pipeline
python scripts/ingest.py

# Expected output:
# - Processing ~112 tender documents
# - Creating ~29,086 vector embeddings
# - Uploading to Qdrant collection
# - Time: ~10-15 minutes (depending on hardware)
```

**Why this is critical:**
- Without this, only metadata queries work
- Vector search (semantic queries) will fail
- 90% of RAG functionality is unavailable

### Step 2: Verify System Components

```bash
# Check Qdrant is running
curl http://localhost:6333/collections

# Check Ollama is running
ollama ps

# Test embeddings model
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('jinaai/jina-embeddings-v3', trust_remote_code=True); print(f'Dim: {m.get_sentence_embedding_dimension()}')"
```

### Step 3: Run Comprehensive Tests

Use the test suites I created:

1. **Quick Test** (5 minutes):
```bash
# Open TEST_QUERIES.md
# Copy/paste queries into Streamlit UI
# Verify responses
```

2. **Full Test** (30 minutes):
```bash
# Use TEST_CHECKLIST.md
# Score each category
# Target: 95%+ pass rate
```

### Step 4: Production Configuration

Create `config_production.py`:

```python
# Production settings
PRODUCTION = True
LOG_LEVEL = "INFO"
MAX_REQUESTS_PER_MINUTE = 30
ENABLE_CACHING = True
CACHE_TTL = 3600  # 1 hour
RESPONSE_TIMEOUT = 10  # seconds
MAX_CONTEXT_LENGTH = 4000  # tokens
```

### Step 5: Monitoring Setup

Create health check endpoint:

```python
# health_check.py
import requests
from qdrant_client import QdrantClient

def check_health():
    checks = {
        "streamlit": False,
        "qdrant": False,
        "ollama": False,
        "metadata": False
    }
    
    # Check Streamlit
    try:
        r = requests.get("http://localhost:8501", timeout=5)
        checks["streamlit"] = r.status_code == 200
    except: pass
    
    # Check Qdrant
    try:
        client = QdrantClient(url="http://localhost:6333")
        collections = client.get_collections()
        checks["qdrant"] = len(collections.collections) > 0
    except: pass
    
    # Check Ollama
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        checks["ollama"] = r.status_code == 200
    except: pass
    
    # Check Metadata
    try:
        import pandas as pd
        df = pd.read_excel("data/metadata/cleaned_metadata.xlsx")
        checks["metadata"] = len(df) > 0
    except: pass
    
    return checks, all(checks.values())

if __name__ == "__main__":
    checks, healthy = check_health()
    print(f"System Health: {'✅ HEALTHY' if healthy else '❌ UNHEALTHY'}")
    for component, status in checks.items():
        print(f"  {component}: {'✅' if status else '❌'}")
```

---

## 🎯 Production-Grade Features

### Already Implemented ✅

1. **Multi-Language Support**
   - English & German queries
   - Automatic language detection
   - Translation fallback

2. **Intelligent Routing**
   - Metadata-first (fast path)
   - Vector search (semantic)
   - Hybrid RRF fusion

3. **Robust Error Handling**
   - Graceful degradation
   - Missing collection handling
   - API timeouts

4. **Quality Measures**
   - BGE reranking
   - Score thresholds
   - Grounding detection

5. **User Experience**
   - Dark theme UI
   - Citation bubbles
   - Chat history
   - Clear feedback

### Needs Implementation 🔨

1. **Caching Layer**
```python
# Add to app_streamlit.py
@st.cache_data(ttl=3600)
def cached_metadata_lookup(query: str):
    return lookup_metadata(query)

@st.cache_resource
def get_embedder():
    return SentenceTransformer(CFG.embed_model, trust_remote_code=True)
```

2. **Rate Limiting**
```python
# Simple rate limiter
from datetime import datetime, timedelta
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_requests=30, window=60):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window)
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id):
        now = datetime.now()
        self.requests[user_id] = [
            ts for ts in self.requests[user_id] 
            if now - ts < self.window
        ]
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True
        return False
```

3. **Logging & Monitoring**
```python
# Enhanced logging
import logging
from pathlib import Path

def setup_production_logging():
    log_dir = Path("logs/production")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    handlers = [
        logging.FileHandler(log_dir / "app.log"),
        logging.FileHandler(log_dir / "errors.log", 
                          level=logging.ERROR),
        logging.StreamHandler()
    ]
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        handlers=handlers
    )
```

4. **Performance Metrics**
```python
# Add response time tracking
import time
from functools import wraps

def track_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper
```

---

## 🔧 Quick Fixes for Production

### 1. Pin Hugging Face Model Revisions

```python
# In core/config.py
EMBED_MODEL_REVISION = "f1944de8402dcd5f2b03f822a4bc22a7f2de2eb9"

# In core/search.py and core/qa.py
m = SentenceTransformer(
    CFG.embed_model, 
    revision=CFG.EMBED_MODEL_REVISION,  # Pin version
    trust_remote_code=True
)
```

### 2. Add Connection Pooling

```python
# In core/search.py
from functools import lru_cache

@lru_cache(maxsize=1)
def _client():
    return QdrantClient(
        url=CFG.qdrant_url, 
        prefer_grpc=False, 
        timeout=60,
        # Add connection pooling
        pool_size=10,
        retries=3
    )
```

### 3. Optimize Batch Processing

```python
# In core/index.py
def index_chunks_batch(chunks, batch_size=100):
    """Process embeddings in batches for efficiency"""
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c.text for c in batch]
        embeddings = embedder.encode(
            texts, 
            batch_size=batch_size,
            show_progress_bar=True
        )
        # Upsert batch
        client.upsert(...)
```

---

## 📊 Performance Targets

### Response Time
- **Metadata queries**: < 0.5s
- **Vector search**: < 3s
- **With reranking**: < 5s
- **LLM generation**: < 10s

### Accuracy
- **Metadata routing**: 100% (deterministic)
- **Vector retrieval**: 85%+ relevance
- **After reranking**: 95%+ relevance
- **Grounding**: 90%+ accuracy

### Availability
- **Uptime**: 99%+
- **Error rate**: < 1%
- **Timeout rate**: < 2%

---

## 🚨 Production Checklist Before Going Live

### Infrastructure
- [ ] Qdrant collection created (29,086 points)
- [ ] Ollama model loaded (qwen2.5:1.5b)
- [ ] Metadata file accessible
- [ ] All logs directories created

### Testing
- [ ] All test queries pass (TEST_QUERIES.md)
- [ ] No errors in last 100 requests
- [ ] Response times within targets
- [ ] Memory usage stable

### Security
- [ ] No API keys in code
- [ ] Input validation on all queries
- [ ] Rate limiting active
- [ ] Error messages sanitized

### Monitoring
- [ ] Health check running
- [ ] Logging configured
- [ ] Metrics collection active
- [ ] Alert system configured

### Documentation
- [ ] User guide created
- [ ] API documentation ready
- [ ] Error codes documented
- [ ] Maintenance procedures written

---

## 🎯 Next Actions (Priority Order)

### 1. CRITICAL: Index Documents (15 min)
```bash
python scripts/ingest.py
```

### 2. HIGH: Verify System (5 min)
```bash
python health_check.py
```

### 3. HIGH: Run Tests (30 min)
- Use TEST_CHECKLIST.md
- Target: 95%+ pass rate

### 4. MEDIUM: Add Production Features (2 hours)
- Implement caching
- Add rate limiting
- Setup monitoring

### 5. LOW: Optimize Performance (ongoing)
- Profile slow queries
- Optimize embeddings
- Tune reranking

---

## 📞 Support & Maintenance

### Daily Checks
- Health endpoint status
- Error log review
- Response time monitoring

### Weekly Tasks
- Performance analysis
- Usage patterns review
- Model updates check

### Monthly Tasks
- Full system backup
- Security audit
- Capacity planning

---

**Last Updated**: October 4, 2025  
**Status**: ✅ App Running | ⚠️ Collection Needs Rebuild  
**Next Step**: Run `python scripts/ingest.py` to enable vector search
