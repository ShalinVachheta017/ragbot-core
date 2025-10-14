# 🎯 Core Improvements Implementation Plan

**Project:** Multilingual RAG Bot for Tender Documents  
**Date:** October 14, 2025  
**Status:** Pre-implementation Planning

---

## 📋 OVERVIEW

This document outlines the 4 core improvements planned for the RAG system:

1. **Hybrid Search** (Dense + BM25 Sparse)
2. **Cross-Encoder Reranker**
3. **Evaluation Framework**
4. **Monitoring Dashboard**

Each improvement is designed to be:
- ✅ **Incremental** - Doesn't break existing functionality
- ✅ **Measurable** - Clear success metrics
- ✅ **Production-ready** - Proper error handling & logging

---

## 🔍 IMPROVEMENT #1: Hybrid Search (Dense + BM25)

### Goal
Combine semantic search (current) with keyword search (new) for better exact-match queries.

### Why?
- Current system uses only dense vectors (Jina v3 embeddings)
- Misses exact keyword matches (CPV codes, DTAD-IDs, specific terms)
- BM25 excels at exact matches, dense excels at semantic similarity

### Implementation Steps

#### Step 1.1: Install Dependencies
```bash
pip install rank-bm25
```

#### Step 1.2: Create `core/hybrid_search.py`
```python
# New file: core/hybrid_search.py
from rank_bm25 import BM25Okapi
import numpy as np
from typing import List, Tuple

class BM25Index:
    """BM25 keyword search index"""
    def __init__(self, documents: List[str]):
        # Tokenize documents
        self.tokenized_docs = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)
        self.documents = documents
    
    def search(self, query: str, top_k: int = 100) -> List[Tuple[str, float]]:
        """Return (doc, score) tuples"""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.documents[i], scores[i]) for i in top_indices]
```

#### Step 1.3: Create BM25 Index During Embedding
Modify `scripts/embed.py` to:
- Build BM25 index alongside vector index
- Save tokenized documents + BM25 scores to disk
- Store in `data/bm25_index.pkl`

#### Step 1.4: Implement Fusion in `core/search.py`
Add new function:
```python
def search_hybrid(query_text: str, alpha: float = 0.7, limit: int = 100):
    """
    Hybrid search: alpha * dense + (1-alpha) * BM25
    alpha=0.7 means 70% semantic, 30% keyword
    """
    # Get dense results
    dense_results = search_dense(query_text, limit=limit)
    
    # Get BM25 results
    bm25_results = bm25_index.search(query_text, top_k=limit)
    
    # Reciprocal Rank Fusion (RRF)
    return rrf([dense_results, bm25_results], k=60)
```

#### Step 1.5: Update `core/qa.py`
Modify `retrieve_candidates()` to:
- Add `use_hybrid: bool = True` parameter
- Call `search_hybrid()` if hybrid enabled
- Fall back to `search_dense()` if hybrid disabled

#### Step 1.6: Add Config Option
Update `core/config.py`:
```python
use_hybrid_search: bool = True
hybrid_alpha: float = 0.7  # 70% dense, 30% BM25
```

### Success Metrics
- ✅ BM25 index builds successfully
- ✅ Hybrid search returns results
- ✅ CPV code queries improve (exact match)
- ✅ DTAD-ID queries improve (exact match)
- ✅ Expected: **+15% recall** on exact-match queries

### Testing
- Query: "CPV 45000000" → Should return exact CPV matches
- Query: "DTAD 20046891" → Should return exact ID match
- Compare before/after hit rates

---

## 🎯 IMPROVEMENT #2: Cross-Encoder Reranker

### Goal
Rerank retrieved chunks before sending to LLM for more relevant context.

### Why?
- Current: Top-K results from vector search go directly to LLM
- Problem: Embedding similarity ≠ actual relevance
- Solution: Cross-encoder scores query-document pairs more accurately

### Implementation Steps

#### Step 2.1: Install Dependencies
```bash
pip install sentence-transformers
```

#### Step 2.2: Create `core/reranker.py`
```python
# New file: core/reranker.py
from sentence_transformers import CrossEncoder
from typing import List, Tuple
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_reranker():
    """Load cross-encoder model (cached singleton)"""
    return CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

class Reranker:
    def __init__(self):
        self.model = _load_reranker()
    
    def rerank(self, query: str, documents: List[str], top_k: int = 8) -> List[Tuple[str, float]]:
        """
        Rerank documents by relevance to query.
        Returns top-k (document, score) tuples.
        """
        # Score all query-document pairs
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs)
        
        # Sort by score descending
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
```

#### Step 2.3: Update `core/qa.py` Pipeline
Modify retrieval pipeline:
```python
def retrieve_candidates(query: str, cfg):
    # Step 1: Fast retrieval (top-100)
    candidates = search_hybrid(query, limit=100)
    
    # Step 2: Reranking (top-8)
    if cfg.use_reranker:
        reranker = Reranker()
        documents = [c.text for c in candidates]
        reranked = reranker.rerank(query, documents, top_k=8)
        # Convert back to candidate format
        return reranked
    
    return candidates[:8]
```

#### Step 2.4: Add Config Options
Update `core/config.py`:
```python
use_reranker: bool = True
reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
reranker_topk: int = 8
retrieval_candidates: int = 100  # Retrieve top-100, rerank to top-8
```

#### Step 2.5: Update UI
Add toggle in `ui/app_streamlit.py`:
```python
use_reranker = st.sidebar.checkbox("Use Reranker", value=True)
```

### Success Metrics
- ✅ Reranker loads without errors
- ✅ Reranking completes in <1 second
- ✅ Expected: **+20% precision** (more relevant top results)

### Testing
- Query: "Mindestlohn requirements" → Check if top results are more relevant
- Compare before/after answer quality
- Measure precision@5

---

## 📊 IMPROVEMENT #3: Evaluation Framework

### Goal
Automated testing suite to measure system quality and track improvements.

### Why?
- Currently: Manual testing only
- Need: Automated regression testing
- Need: Quantitative metrics to measure improvements

### Implementation Steps

#### Step 3.1: Create Directory Structure
```
eval/
├── test_queries.json      # Test set with 50+ queries
├── ground_truth.json      # Expected answers/documents
├── metrics.py             # Metric calculations
├── run_evaluation.py      # Main evaluation script
├── compare_systems.py     # A/B testing script
└── reports/               # Generated HTML reports
```

#### Step 3.2: Create Test Set (`eval/test_queries.json`)
```json
{
  "queries": [
    {
      "id": "simple_001",
      "category": "dtad_lookup",
      "query": "Was ist DTAD-ID 20046891?",
      "expected_docs": ["20046891/main.pdf"],
      "expected_answer_contains": ["20046891", "Titel"]
    },
    {
      "id": "temporal_001",
      "category": "temporal",
      "query": "Tenders from 2024",
      "expected_docs": ["20047*"],
      "min_results": 10
    },
    // ... 48 more queries
  ]
}
```

#### Step 3.3: Implement Metrics (`eval/metrics.py`)
```python
def hit_rate(retrieved_docs, relevant_docs):
    """Did we retrieve at least one relevant doc?"""
    return 1.0 if any(d in relevant_docs for d in retrieved_docs) else 0.0

def mean_reciprocal_rank(retrieved_docs, relevant_docs):
    """MRR: 1 / rank of first relevant doc"""
    for i, doc in enumerate(retrieved_docs, 1):
        if doc in relevant_docs:
            return 1.0 / i
    return 0.0

def precision_at_k(retrieved_docs, relevant_docs, k):
    """Precision@K: % of top-k that are relevant"""
    top_k = retrieved_docs[:k]
    relevant_count = sum(1 for d in top_k if d in relevant_docs)
    return relevant_count / k

def recall_at_k(retrieved_docs, relevant_docs, k):
    """Recall@K: % of relevant docs in top-k"""
    top_k = retrieved_docs[:k]
    relevant_count = sum(1 for d in top_k if d in relevant_docs)
    return relevant_count / len(relevant_docs)

def answer_faithfulness(answer, sources):
    """Check if answer is grounded in sources (simple version)"""
    # TODO: Use LLM to check if answer is supported by sources
    pass
```

#### Step 3.4: Create Evaluation Runner (`eval/run_evaluation.py`)
```python
import json
from core.qa import retrieve_candidates
from eval.metrics import *

def run_evaluation(config_name="baseline"):
    results = []
    
    # Load test queries
    with open('eval/test_queries.json') as f:
        test_data = json.load(f)
    
    for query_obj in test_data['queries']:
        query = query_obj['query']
        expected_docs = query_obj['expected_docs']
        
        # Run retrieval
        retrieved = retrieve_candidates(query, CFG)
        retrieved_docs = [r.source for r in retrieved]
        
        # Calculate metrics
        metrics = {
            'hit_rate': hit_rate(retrieved_docs, expected_docs),
            'mrr': mean_reciprocal_rank(retrieved_docs, expected_docs),
            'precision@5': precision_at_k(retrieved_docs, expected_docs, 5),
            'recall@5': recall_at_k(retrieved_docs, expected_docs, 5),
        }
        
        results.append({
            'query_id': query_obj['id'],
            'category': query_obj['category'],
            'metrics': metrics
        })
    
    # Aggregate by category
    return aggregate_results(results)
```

#### Step 3.5: Create A/B Testing Script (`eval/compare_systems.py`)
```python
def compare_systems(config_a, config_b):
    """Compare two system configurations"""
    results_a = run_evaluation(config_a)
    results_b = run_evaluation(config_b)
    
    # Statistical comparison
    print(f"Hit Rate: {results_a['hit_rate']} vs {results_b['hit_rate']}")
    print(f"MRR: {results_a['mrr']} vs {results_b['mrr']}")
    # ... more comparisons
```

### Success Metrics
- ✅ 50+ test queries created
- ✅ All metrics run without errors
- ✅ HTML report generated
- ✅ Baseline metrics established

### Testing
- Run: `python eval/run_evaluation.py`
- Compare: Dense vs Hybrid vs Reranked
- Track improvements over time

---

## 📈 IMPROVEMENT #4: Monitoring Dashboard

### Goal
Track system performance and errors in production.

### Why?
- Currently: No visibility into performance
- Need: Real-time metrics (latency, errors, query patterns)
- Need: Alerts for issues

### Implementation Steps

#### Step 4.1: Create Directory Structure
```
monitoring/
├── metrics.py           # Metrics collection
├── storage.py           # SQLite storage
├── dashboard.py         # Streamlit dashboard
├── alerts.py            # Alert rules
└── metrics.db           # SQLite database
```

#### Step 4.2: Create Metrics Tracker (`monitoring/metrics.py`)
```python
import time
import sqlite3
from datetime import datetime
from contextlib import contextmanager

class MetricsTracker:
    def __init__(self, db_path="monitoring/metrics.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if not exist"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS query_metrics (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                query TEXT,
                latency_ms REAL,
                num_results INTEGER,
                error TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    @contextmanager
    def track_query(self, query: str):
        """Context manager to track query performance"""
        start_time = time.time()
        error = None
        num_results = 0
        
        try:
            yield
        except Exception as e:
            error = str(e)
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            self._log_query(query, latency_ms, num_results, error)
    
    def _log_query(self, query, latency_ms, num_results, error):
        """Log query metrics to database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO query_metrics (timestamp, query, latency_ms, num_results, error, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            query,
            latency_ms,
            num_results,
            error,
            'error' if error else 'success'
        ))
        conn.commit()
        conn.close()
```

#### Step 4.3: Update `core/qa.py` to Track Metrics
```python
from monitoring.metrics import MetricsTracker

metrics = MetricsTracker()

def answer_query(query: str):
    with metrics.track_query(query):
        # Existing logic
        results = retrieve_candidates(query, CFG)
        answer = generate_answer(query, results)
        return answer
```

#### Step 4.4: Create Dashboard (`monitoring/dashboard.py`)
```python
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3

st.title("📈 RAG System Monitoring")

# Load metrics
conn = sqlite3.connect("monitoring/metrics.db")
df = pd.read_sql_query("SELECT * FROM query_metrics", conn)
conn.close()

# Overview metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Queries", len(df))
col2.metric("Avg Latency", f"{df['latency_ms'].mean():.0f}ms")
col3.metric("Error Rate", f"{(df['status']=='error').mean()*100:.1f}%")
col4.metric("P95 Latency", f"{df['latency_ms'].quantile(0.95):.0f}ms")

# Latency over time
fig = px.line(df, x='timestamp', y='latency_ms', title='Query Latency Over Time')
st.plotly_chart(fig)

# Error log
st.subheader("Recent Errors")
errors = df[df['status'] == 'error'].tail(10)
st.dataframe(errors[['timestamp', 'query', 'error']])

# Slow queries (>5s)
st.subheader("Slow Queries (>5s)")
slow = df[df['latency_ms'] > 5000].tail(10)
st.dataframe(slow[['timestamp', 'query', 'latency_ms']])
```

#### Step 4.5: Create Alert Rules (`monitoring/alerts.py`)
```python
def check_alerts():
    """Check for alert conditions"""
    conn = sqlite3.connect("monitoring/metrics.db")
    
    # Alert: Error rate > 5% in last hour
    error_rate = conn.execute('''
        SELECT AVG(CASE WHEN status='error' THEN 1 ELSE 0 END) as error_rate
        FROM query_metrics
        WHERE timestamp > datetime('now', '-1 hour')
    ''').fetchone()[0]
    
    if error_rate > 0.05:
        send_alert(f"High error rate: {error_rate*100:.1f}%")
    
    # Alert: Latency p95 > 10s
    p95_latency = conn.execute('''
        SELECT latency_ms
        FROM query_metrics
        WHERE timestamp > datetime('now', '-1 hour')
        ORDER BY latency_ms DESC
        LIMIT 1 OFFSET (SELECT COUNT(*)*0.05 FROM query_metrics WHERE timestamp > datetime('now', '-1 hour'))
    ''').fetchone()[0]
    
    if p95_latency > 10000:
        send_alert(f"High p95 latency: {p95_latency:.0f}ms")
    
    conn.close()
```

#### Step 4.6: Link from Main UI
Update `ui/app_streamlit.py`:
```python
st.sidebar.markdown("---")
st.sidebar.markdown("[📈 Monitoring Dashboard](http://localhost:8502)")
```

### Success Metrics
- ✅ Metrics logged successfully
- ✅ Dashboard displays correctly
- ✅ Alerts trigger when thresholds exceeded
- ✅ Query patterns identified

### Testing
- Run queries, verify metrics logged
- Launch dashboard: `streamlit run monitoring/dashboard.py --server.port 8502`
- Trigger alert by simulating errors

---

## 📅 IMPLEMENTATION TIMELINE

### Week 1: Cleanup + Hybrid Search
- Day 1-2: File cleanup
- Day 3-5: Implement hybrid search
- Day 6-7: Test and validate

### Week 2: Reranker + Evaluation
- Day 1-3: Implement reranker
- Day 4-7: Build evaluation framework

### Week 3: Monitoring + Polish
- Day 1-4: Build monitoring dashboard
- Day 5-7: Final testing, documentation

---

## 🎯 SUCCESS CRITERIA

### Overall Goals
- ✅ All 4 improvements implemented
- ✅ System passes evaluation tests
- ✅ Monitoring shows stable performance
- ✅ Documentation updated

### Quantitative Metrics
- **+15% recall** (hybrid search)
- **+20% precision** (reranker)
- **<3s latency** (p95)
- **<5% error rate**

### Qualitative Goals
- ✅ Better exact-match queries (CPV, DTAD-IDs)
- ✅ More relevant search results
- ✅ Production visibility (monitoring)
- ✅ Automated testing (no manual regression)

---

## 🚀 LET'S GET STARTED!

**Next Step:** Execute Phase 1 cleanup from FILE_AUDIT.md

Once cleanup is done, we'll begin with Improvement #1: Hybrid Search! 🔥
