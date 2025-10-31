# Quick Test Queries - Copy & Paste Ready
**For RAG System Evaluation**

---

## 🚀 QUICK START (Copy these into Streamlit)

### ✅ Test 1: Metadata Lookup
```
20046891
```

### ✅ Test 2: Semantic Search (English)
```
What are the requirements for road construction projects?
```

### ✅ Test 3: Semantic Search (German)
```
Welche Anforderungen gibt es für Straßenbauprojekte?
```

### ✅ Test 4: Year Filter
```
Show me all tenders from 2024
```

### ✅ Test 5: Region Filter
```
tenders in Berlin
```

### ✅ Test 6: Combined Filter
```
construction tenders from 2024 in Bavaria
```

### ✅ Test 7: Delivery Deadline
```
What is the delivery deadline for tender 20046891?
```

### ✅ Test 8: Budget Information
```
What is the estimated budget for construction projects?
```

### ✅ Test 9: Technical Specs
```
What technical specifications are required?
```

### ✅ Test 10: Qualifications
```
What qualifications do contractors need?
```

---

## 🇩🇪 GERMAN QUERIES

### Test 11: Lieferfrist (Deadline)
```
Was ist die Lieferfrist für Ausschreibung 20046891?
```

### Test 12: Vergabestelle (Authority)
```
Welche Vergabestelle ist für dieses Projekt verantwortlich?
```

### Test 13: Ausschreibung Details
```
Zeige mir Details zur Ausschreibung für Tiefbauarbeiten
```

### Test 14: Budget (German)
```
Was ist das Budget für Straßenbauprojekte?
```

### Test 15: Anforderungen (Requirements)
```
Welche technischen Anforderungen gibt es?
```

---

## 🎯 DOMAIN-SPECIFIC

### Test 16: VOB Regulations
```
What VOB regulations apply to these tenders?
```

### Test 17: DIN Standards
```
Which DIN standards are required for construction?
```

### Test 18: Construction Types
```
What types of construction services are included in the tenders?
```

### Test 19: Bauleistungen
```
Was für Bauleistungen sind in den Ausschreibungen enthalten?
```

---

## 🔍 COMPLEX QUERIES

### Test 20: Multi-Criteria
```
Find tenders for road construction in 2024 with budget over 1 million euros
```

### Test 21: Comparative
```
Compare requirements between tender 20046891 and 20046645
```

### Test 22: Temporal
```
What tenders are closing this month?
```

### Test 23: Geographic
```
Show me all tenders in southern Germany
```

---

## ⚠️ GROUNDING TESTS (Should Warn)

### Test 24: General Knowledge
```
What is the capital of France?
```
**Expected**: Warning that this is not in tender data

### Test 25: Current Events
```
Who won the 2025 World Cup?
```
**Expected**: "Not in the tender data"

### Test 26: Math
```
What is 2 + 2?
```
**Expected**: Simple answer but with grounding warning

### Test 27: Out of Scope
```
What are tender opportunities in France?
```
**Expected**: "Not in tender data" (only German tenders)

---

## 🧪 EDGE CASES

### Test 28: Very Short Query
```
Berlin
```

### Test 29: Long Query
```
I am looking for comprehensive information about road construction projects that involve infrastructure development including highways autobahns bridges tunnels and other transportation related construction work currently being tendered in Germany with focus on technical requirements budget constraints delivery timelines and qualification criteria
```

### Test 30: Special Characters
```
What about § 123 paragraph (2) clause [a-c]?
```

### Test 31: Numbers Only
```
2024 500000 Berlin
```

### Test 32: Malformed DTAD-ID
```
20046
```
**Expected**: No match, suggests correct format

### Test 33: Empty Query
```

```
**Expected**: Error message or prompt

---

## 💬 CONVERSATION TESTS

### Test 34: Follow-Up (Multi-Turn)
**First**: 
```
What is DTAD-ID 20046891 about?
```
**Then**: 
```
What is the deadline?
```
**Expected**: Uses context from first query

### Test 35: Refinement
**First**: 
```
construction tenders
```
**Then**: 
```
I meant specifically road construction
```

### Test 36: Multi-Step
**Step 1**: 
```
Show me tenders in Berlin
```
**Step 2**: 
```
Which ones are for road construction?
```
**Step 3**: 
```
What are the budgets?
```

---

## 🌐 TRANSLATION TESTS

### Test 37: German → English
1. Ask: `Welche Anforderungen gibt es für Straßenbau?`
2. Get answer in German
3. Click "🌐 Translate last answer" → Select "English"
4. Verify translation

### Test 38: English → German
1. Ask: `What are the road construction requirements?`
2. Get answer in English
3. Click "🌐 Translate last answer" → Select "Deutsch"
4. Verify translation

---

## 📊 PERFORMANCE TESTS

### Test 39: Response Time - Fast
```
20046891
```
**Measure**: Should be < 500ms

### Test 40: Response Time - Semantic
```
road construction requirements
```
**Measure**: Should be < 5 seconds total

---

## 🎯 CITATION VERIFICATION

### Test 41: Check Sources
```
What are the requirements for road construction?
```
**Then**:
- Check citations [1], [2], etc.
- Download source PDF
- Verify text appears on cited page
- Check scores (should be > 0.5)

---

## 🔧 UI FEATURE TESTS

### Test 42: Adjust Top-K
1. Set Top-K slider to 5
2. Ask: `construction requirements`
3. Count sources (should be exactly 5)

### Test 43: Temperature Effect
1. Set temperature to 0.0
2. Ask: `Summarize tender requirements`
3. Note answer
4. Set temperature to 1.0
5. Ask same question
6. Compare answers

### Test 44: Clear History
1. Ask 3 questions
2. Click "🧹 Clear history"
3. Verify all messages gone

### Test 45: Export Chat
1. Have some conversation
2. Click "⬇️ Export chat (.md)"
3. Open downloaded file

### Test 46: Debug Mode
1. Enable "Show retrieved chunks"
2. Submit any query
3. Check raw chunk display

---

## ⚡ RAPID TESTING SEQUENCE (5 minutes)

Copy and paste these in order:

1. `20046891`
2. `road construction requirements`
3. `Welche Anforderungen für Straßenbau?`
4. `tenders from 2024`
5. `What is the capital of France?`
6. `What is the deadline?` (follow-up)
7. Then download a PDF source
8. Then translate an answer
9. Then clear history
10. Done!

---

## 📋 CHECKLIST WHILE TESTING

For each query, check:
- [ ] Response received (no crash)
- [ ] Response time reasonable (< 10 sec)
- [ ] Citations present [1], [2], etc.
- [ ] Sources downloadable
- [ ] Scores > 0.5 for top results
- [ ] Answer in correct language
- [ ] Grounding detection works (if off-topic)
- [ ] No hallucination

---

## 🎯 EXPECTED BEHAVIOR SUMMARY

| Query Type | Expected Response Time | Expected Score | Grounded? |
|------------|------------------------|----------------|-----------|
| DTAD-ID lookup | < 500ms | N/A | Yes |
| Semantic search | 2-5 sec | > 0.6 | Yes |
| Year/Region filter | < 1 sec | N/A | Yes |
| German query | 2-5 sec | > 0.6 | Yes |
| Off-topic | 1-3 sec | N/A | No (warning) |
| Follow-up | 2-5 sec | > 0.5 | Yes |

---

## 🐛 IF SOMETHING GOES WRONG

### No Results / Empty Response
- Check Qdrant is running: `docker ps | grep qdrant`
- Verify collection exists: `curl http://localhost:6333/collections`

### Slow Response
- Check GPU usage
- Reduce Top-K value
- Disable reranker temporarily

### Wrong Language Response
- Check query language detection
- Try being more explicit: "Answer in German please"

### LLM Error
- Check Ollama is running: `ollama ps`
- Verify model loaded: `ollama list`

### Import Errors (on restart)
- Rerun: `conda activate mllocalag`
- Check: `python -c "import streamlit, qdrant_client, ollama"`

---

**Happy Testing! 🚀**

Start with the Rapid Testing Sequence, then explore specific categories based on your priorities.
