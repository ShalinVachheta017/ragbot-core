# 🎯 Sample Test Queries for Tender RAG System

**Purpose:** Test different query types to evaluate system performance  
**Use:** Try these queries in the Streamlit UI or save for evaluation framework

---

## 📋 Category 1: Direct DTAD-ID Lookups (Metadata Routing)

**Expected behavior:** Should retrieve exact document via metadata, instant response

### German Queries:
1. `Was ist DTAD-ID 20046891?`
2. `Zeige mir DTAD 20046893`
3. `Details zu Vergabe 20047108`
4. `DTAD-ID 20046690 Informationen`
5. `Tender 20047337 anzeigen`

### English Queries:
6. `What is DTAD-ID 20046891?`
7. `Show me tender 20047108`
8. `Details for DTAD 20046893`
9. `Information about tender ID 20046690`
10. `Display DTAD-ID 20047337`

**Success Metric:** Should find document in <500ms, exact match

---

## 📅 Category 2: Temporal Queries (Date/Year Filtering)

**Expected behavior:** Filter by date/year in metadata

### German Queries:
11. `Ausschreibungen aus 2024`
12. `Zeige mir Tender von 2023`
13. `Welche Vergaben wurden im März 2024 veröffentlicht?`
14. `Tender aus dem ersten Quartal 2024`
15. `Neueste Ausschreibungen`

### English Queries:
16. `Tenders from 2024`
17. `Show me tenders published in 2023`
18. `What tenders were published in March 2024?`
19. `Tenders from Q1 2024`
20. `Recent tenders`

**Success Metric:** Should return 10+ relevant documents, filtered by date

---

## 🌍 Category 3: Geographic/Regional Queries

**Expected behavior:** Filter by region/location in metadata

### German Queries:
21. `Ausschreibungen in Dresden`
22. `Tender in Sachsen`
23. `Vergaben in Berlin`
24. `Projekte in Hessen`
25. `Ausschreibungen in Oedhein` (specific town)
26. `Zeige mir alle Tender in Wilhelmshaven`

### English Queries:
27. `Tenders in Dresden`
28. `Show me projects in Berlin`
29. `Tenders from Saxony region`
30. `Contracts in Hessen in 2023`

**Success Metric:** Should return region-specific documents, 5+ results

---

## 🔍 Category 4: CPV Code / Category Queries (Exact Match)

**Expected behavior:** Should benefit from hybrid search (BM25 exact match)

### German Queries:
31. `CPV 45000000 Ausschreibungen`
32. `Bauarbeiten Ausschreibungen` (construction)
33. `IT-Projekte Tender`
34. `Sanierungsarbeiten Vergaben`
35. `Garten- und Landschaftsbau Ausschreibungen`

### English Queries:
36. `CPV 45000000 tenders`
37. `Construction tenders`
38. `IT project tenders`
39. `Renovation tenders`
40. `Landscaping tenders`

**Success Metric:** Exact CPV code match, category-specific results

---

## 🧠 Category 5: Semantic / Domain-Specific Questions

**Expected behavior:** Dense search performs well, needs understanding

### German Queries:
41. `Welche Unterlagen sind für VOB-konforme Ausschreibungen erforderlich?`
42. `Was sind die Anforderungen für Mindestlohn in Bauausschreibungen?`
43. `Wie funktioniert der Vergabeprozess?`
44. `Welche Fristen gelten für Angebotsabgaben?`
45. `Was ist bei der technischen Spezifikation zu beachten?`
46. `Welche Versicherungen werden verlangt?`
47. `Was sind die Zahlungsbedingungen?`

### English Queries:
48. `What documents are required for VOB-compliant tenders?`
49. `What are the minimum wage requirements in construction tenders?`
50. `How does the procurement process work?`
51. `What deadlines apply for bid submissions?`
52. `What should be considered in technical specifications?`
53. `What insurance is required?`
54. `What are the payment terms?`

**Success Metric:** Contextually relevant answers, cites multiple sources

---

## 🎯 Category 6: Complex Multi-Hop Queries

**Expected behavior:** Requires combining multiple documents/facts

### German Queries:
55. `Vergleiche die Anforderungen zwischen Tender 20046891 und 20046893`
56. `Was hat sich bei Dresden Ausschreibungen von 2023 zu 2024 geändert?`
57. `Welche Tender in Sachsen haben die höchsten Budgets?`
58. `Zeige mir ähnliche Tender wie 20047108`
59. `Welche Bauausschreibungen in Berlin erfordern VOB-Konformität?`

### English Queries:
60. `Compare requirements between tender 20046891 and 20046893`
61. `What changed in Dresden tenders from 2023 to 2024?`
62. `Which tenders in Saxony have the highest budgets?`
63. `Show me tenders similar to 20047108`
64. `Which construction tenders in Berlin require VOB compliance?`

**Success Metric:** Multi-document synthesis, comparative analysis

---

## ❌ Category 7: Edge Cases / Failure Modes

**Expected behavior:** Graceful handling of edge cases

### Queries that SHOULD fail gracefully:
65. `DTAD-ID 99999999` (non-existent ID)
66. `Tender aus dem Jahr 2030` (future date)
67. `Ausschreibungen in Atlantis` (non-existent location)
68. `CPV 99999999999` (invalid CPV code)
69. `Random nonsense query xyz 123` (gibberish)
70. `` (empty query)

### Queries with typos/variations:
71. `DTAD 2004689` (missing digit)
72. `Tender in Dreden` (typo: Dresden)
73. `Ausschreibunge` (typo: Ausschreibungen)
74. `CPV4500000` (missing space)

**Success Metric:** Clear "no results" or "did you mean..." message

---

## 🌐 Category 8: Multilingual / Mixed Language

**Expected behavior:** Should handle code-switching

75. `Show me tenders in Dresden from 2024` (English + German place)
76. `Was ist CPV 45000000?` (German + English code)
77. `Tender requirements für Bauarbeiten` (mixed)
78. `Welche documents brauche ich?` (mixed)

**Success Metric:** Understands intent regardless of language mix

---

## 🔤 Category 9: Abbreviations & Domain Terms

**Expected behavior:** Should expand/understand abbreviations

79. `VOB Ausschreibungen`
80. `Tender mit Eignungsprüfung`
81. `EU-weite Vergaben`
82. `GU Ausschreibungen` (Generalunternehmer)
83. `HOAI konforme Projekte`

**Success Metric:** Finds relevant documents with domain understanding

---

## 📊 Category 10: Aggregation / Statistical Queries

**Expected behavior:** May need future enhancement (agentic RAG)

84. `Wie viele Tender gibt es in Dresden?`
85. `Durchschnittliches Budget für Bauausschreibungen`
86. `Welche Region hat die meisten Ausschreibungen?`
87. `Häufigste CPV Codes`

**Success Metric:** Currently may not work well, good for future eval

---

## 🎯 QUICK START TEST SET (10 Essential Queries)

**Use these 10 to quickly test system after changes:**

1. ✅ `Was ist DTAD-ID 20046891?` (exact match)
2. ✅ `Tenders from 2024` (temporal)
3. ✅ `Ausschreibungen in Dresden` (geographic)
4. ✅ `CPV 45000000` (exact code)
5. ✅ `Mindestlohn requirements` (semantic)
6. ✅ `Construction tenders in Berlin` (combined filters)
7. ✅ `Welche Unterlagen sind erforderlich?` (open question)
8. ✅ `Show me tender 20047108` (English exact match)
9. ❌ `DTAD-ID 99999999` (non-existent, should fail gracefully)
10. ✅ `Similar tenders to 20046893` (semantic similarity)

---

## 📈 EXPECTED PERFORMANCE BY CATEGORY

| Category | Current (Dense Only) | After Hybrid | After Reranker |
|----------|---------------------|--------------|----------------|
| DTAD Lookups | 95% ✅ | 95% ✅ | 95% ✅ |
| Temporal | 80% 🟡 | 85% 🟢 | 90% 🟢 |
| Geographic | 75% 🟡 | 80% 🟢 | 85% 🟢 |
| CPV/Exact Match | 60% 🔴 | **85% 🟢** | 90% 🟢 |
| Semantic | 85% 🟢 | 85% 🟢 | **95% 🟢** |
| Complex Multi-hop | 50% 🔴 | 60% 🟡 | **75% 🟢** |
| Edge Cases | 70% 🟡 | 75% 🟡 | 80% 🟢 |

**Key Improvements Expected:**
- 🔥 Hybrid Search: +25% on exact match queries (CPV, DTAD typos)
- 🔥 Reranker: +10-20% on semantic and complex queries
- 🔥 Combined: +30% overall accuracy

---

## 💾 SAVE FOR EVALUATION

**When building evaluation framework:**
- Save queries 1-64 to `eval/test_queries.json`
- Create ground truth (expected DTAD-IDs per query)
- Track metrics before/after each improvement
- Use for regression testing

---

## 🚀 HOW TO USE RIGHT NOW

### Option 1: Manual Testing (Quick)
1. Start Streamlit: `streamlit run ui/app_streamlit.py`
2. Copy-paste queries above
3. Check if results make sense
4. Note any failures

### Option 2: Automated Script (Better)
```python
# Create simple test script
import requests

queries = [
    "Was ist DTAD-ID 20046891?",
    "Tenders from 2024",
    # ... add more
]

for q in queries:
    # Call your RAG system
    result = answer_query(q)
    print(f"Q: {q}")
    print(f"A: {result[:100]}...")
    print("-" * 50)
```

### Option 3: Full Evaluation (After Building Framework)
- Use queries in `eval/test_queries.json`
- Run `python eval/run_evaluation.py`
- Get quantitative metrics (Hit Rate, MRR, etc.)

---

**Next:** Try the Quick Start Test Set (10 queries) to baseline current performance! 🎯
