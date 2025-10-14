# 🤔 Evaluation Strategy: Now vs Later with RAGAS

**Decision Guide:** Should you evaluate now or wait until after improvements?

---

## 📊 TL;DR RECOMMENDATION

### ✅ **DO NOW (Before Improvements):**
1. **Manual baseline testing** (30 min)
   - Try 10 Quick Start queries from `SAMPLE_QUERIES.md`
   - Document what works and what doesn't
   - Take notes on answer quality

2. **Simple automated baseline** (1 hour)
   - Create basic test script with 20-30 queries
   - Track: response time, whether answer was generated, basic relevance
   - No fancy metrics yet

### ⏳ **DO LATER (After Hybrid + Reranker):**
1. **Full RAGAS evaluation framework** (4-6 hours to build properly)
   - Complete test set (50+ queries with ground truth)
   - RAGAS metrics (faithfulness, answer_relevancy, context_precision, context_recall)
   - A/B comparison between systems

---

## 🎯 WHY EVALUATE IN PHASES?

### Phase 1: NOW (Baseline) - Quick & Manual
**Goal:** Understand current system's strengths/weaknesses

**What to do:**
```python
# Quick baseline test (save to test_baseline.py)
from core.qa import answer_query

test_queries = [
    "Was ist DTAD-ID 20046891?",
    "Tenders from 2024",
    "Ausschreibungen in Dresden",
    "CPV 45000000",
    "Mindestlohn requirements",
]

for q in test_queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    try:
        result = answer_query(q)
        print(f"Answer: {result['answer'][:200]}...")
        print(f"Sources: {len(result['sources'])} documents")
    except Exception as e:
        print(f"ERROR: {e}")
```

**Benefits:**
- ✅ Takes 30-60 minutes
- ✅ Identifies obvious problems
- ✅ Establishes baseline expectations
- ✅ Doesn't slow down implementation

**Limitations:**
- ❌ No quantitative metrics
- ❌ Manual judgment only
- ❌ Not repeatable/automated

---

### Phase 2: LATER (Full RAGAS) - Automated & Comprehensive
**Goal:** Quantitative metrics to prove improvements

**What to do:**
Build complete evaluation framework with:
```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

# After you have:
# 1. Test queries with ground truth
# 2. Multiple system versions to compare
# 3. Time to build proper eval pipeline

results = evaluate(
    dataset=test_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)
```

**Benefits:**
- ✅ Quantitative proof of improvements
- ✅ Reproducible benchmarks
- ✅ Detailed failure analysis
- ✅ Publication-ready metrics

**Limitations:**
- ❌ Takes 4-6 hours to build properly
- ❌ Requires ground truth annotations
- ❌ Needs LLM API (for RAGAS metrics)
- ❌ Slows down rapid iteration

---

## ⚖️ COMPARISON: Now vs Later

| Aspect | Simple Baseline (NOW) | RAGAS Framework (LATER) |
|--------|----------------------|------------------------|
| **Time to setup** | 30-60 min | 4-6 hours |
| **Queries needed** | 10-30 | 50-100+ |
| **Ground truth** | Not needed | Required |
| **Metrics** | Pass/fail, subjective | Quantitative scores |
| **Automation** | Manual or simple script | Fully automated |
| **Repeatability** | Low | High |
| **Best for** | Quick iteration | Final validation |
| **Blocks progress?** | No | Yes (if done first) |

---

## 🚦 DECISION TREE

### Do Simple Baseline NOW if:
- ✅ You want to start coding improvements quickly
- ✅ You need to identify obvious problems first
- ✅ You're iterating rapidly (try → fix → try)
- ✅ You haven't built eval frameworks before

### Do RAGAS Framework FIRST if:
- ✅ You need quantitative proof for stakeholders
- ✅ You're comparing multiple approaches (research)
- ✅ You have time budget (not under deadline)
- ✅ You have experience with RAGAS already

---

## 🎬 RECOMMENDED WORKFLOW

### Week 1: Baseline + Hybrid Search
```
Day 1: ✅ Manual baseline testing (30 min)
       → Try 10 queries, document issues
       
Day 2-5: 🔥 Implement hybrid search
         → Add BM25 index
         → Implement fusion
         → Test with same 10 queries
         
Day 6: ✅ Compare before/after manually
       → "CPV queries work better now!"
```

### Week 2: Reranker + Simple Automation
```
Day 1-3: 🔥 Implement reranker
         → Add cross-encoder
         → Wire into pipeline
         
Day 4: ✅ Create simple test script (1 hour)
       → Run 30 queries automatically
       → Track: success rate, avg time
       
Day 5: ✅ Compare: Dense vs Hybrid vs Reranked
       → Basic metrics sufficient
```

### Week 3: Full RAGAS Framework
```
Day 1-2: 📊 Build evaluation suite
         → Create test_queries.json (50+ queries)
         → Annotate ground truth
         
Day 3-4: 🧪 Implement RAGAS metrics
         → Install dependencies
         → Set up OpenAI API (for RAGAS)
         → Run evaluation
         
Day 5: 📈 Analyze & document results
       → Generate report
       → Update README with metrics
```

---

## 🔍 MINIMAL VIABLE BASELINE (Do This NOW)

Here's a 30-minute baseline test you can run right now:

```python
# test_baseline.py - Save this file and run it

import time
from core.qa import answer_query

# Test categories
test_suite = {
    "Exact Match (DTAD)": [
        "Was ist DTAD-ID 20046891?",
        "Show me tender 20047108",
    ],
    "Temporal": [
        "Tenders from 2024",
        "Ausschreibungen aus 2023",
    ],
    "Geographic": [
        "Ausschreibungen in Dresden",
        "Tenders in Berlin",
    ],
    "Exact Code (CPV)": [
        "CPV 45000000",
        "Construction tenders CPV 45000000",
    ],
    "Semantic": [
        "Mindestlohn requirements",
        "VOB compliance requirements",
    ],
}

print("🧪 BASELINE EVALUATION")
print("=" * 60)

results = {}
for category, queries in test_suite.items():
    print(f"\n📋 Category: {category}")
    print("-" * 60)
    
    category_results = []
    for query in queries:
        start = time.time()
        try:
            result = answer_query(query)
            latency = (time.time() - start) * 1000
            
            # Basic quality check
            has_answer = len(result.get('answer', '')) > 50
            has_sources = len(result.get('sources', [])) > 0
            
            status = "✅" if (has_answer and has_sources) else "❌"
            
            print(f"  {status} {query[:50]}...")
            print(f"     Latency: {latency:.0f}ms | Sources: {len(result.get('sources', []))}")
            
            category_results.append({
                'query': query,
                'success': has_answer and has_sources,
                'latency_ms': latency,
                'num_sources': len(result.get('sources', []))
            })
            
        except Exception as e:
            print(f"  ❌ {query[:50]}... ERROR: {str(e)[:50]}")
            category_results.append({
                'query': query,
                'success': False,
                'error': str(e)
            })
    
    results[category] = category_results

# Summary
print("\n" + "=" * 60)
print("📊 SUMMARY")
print("=" * 60)

total_queries = sum(len(r) for r in results.values())
total_success = sum(sum(1 for q in r if q.get('success')) for r in results.values())

print(f"\nOverall Success Rate: {total_success}/{total_queries} ({total_success/total_queries*100:.1f}%)")

for category, category_results in results.items():
    success = sum(1 for q in category_results if q.get('success'))
    total = len(category_results)
    print(f"  {category}: {success}/{total} ({success/total*100:.1f}%)")

print("\n💾 Save these results to compare after improvements!")
```

**Run it:**
```bash
python test_baseline.py
```

**Takes:** 30 minutes (10 queries × ~3min each)  
**Gives you:** 
- Success rate per category
- Latency benchmarks
- Specific failing queries to investigate

---

## 📈 WHEN TO BUILD FULL RAGAS FRAMEWORK

Build the complete evaluation framework **AFTER** you've implemented:
1. ✅ Hybrid search
2. ✅ Reranker
3. ✅ Basic improvements working

**Why?** Because then you'll have:
- Multiple system versions to compare
- Clear improvement hypothesis to test
- Motivation to prove your improvements work
- Better understanding of what metrics matter

**Timing:** Week 3 or after core improvements are done

---

## 🎯 RAGAS FRAMEWORK PREVIEW

When you DO build it (later), here's what you'll create:

```python
# eval/run_evaluation.py (Future)

from ragas import evaluate
from ragas.metrics import (
    faithfulness,           # Answer grounded in sources?
    answer_relevancy,       # Answer relevant to question?
    context_precision,      # Retrieved docs relevant?
    context_recall,         # All relevant docs retrieved?
)
from datasets import Dataset

# Load test data
test_data = {
    "question": [...],          # Your queries
    "answer": [...],            # System's answers
    "contexts": [...],          # Retrieved documents
    "ground_truth": [...]       # Expected answers (optional)
}

dataset = Dataset.from_dict(test_data)

# Evaluate
results = evaluate(
    dataset=dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]
)

print(results)
```

**But you need:**
- OpenAI API key (RAGAS uses GPT-4 for evaluation)
- Ground truth annotations (expected answers)
- Proper test dataset (50+ queries)

**Cost:** ~$5-10 for 50 queries (OpenAI API calls)

---

## ✅ FINAL RECOMMENDATION

### Do This NOW (30 min):
1. Run the simple baseline test script above
2. Note what categories fail
3. Move on to implementing improvements

### Do This LATER (Week 3):
1. Build full RAGAS evaluation framework
2. Compare before/after quantitatively
3. Use for regression testing going forward

**Reason:** Don't let perfect be the enemy of good. A simple baseline is enough to guide improvements. Build the fancy evaluation framework AFTER you have something to compare against!

---

## 🚀 IMMEDIATE ACTION

**Right now, open Streamlit and try these 5 queries:**

1. `Was ist DTAD-ID 20046891?` ← Should work perfectly
2. `CPV 45000000` ← Might struggle (exact match)
3. `Tenders from 2024` ← Should work
4. `Mindestlohn requirements` ← Check answer quality
5. `Compare tender 20046891 and 20046893` ← Will probably fail

**Document what works and what doesn't. That's your baseline!** ✅

Then start building hybrid search to improve #2 (exact matches). 🚀
