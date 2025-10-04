# RAG System - Comprehensive Test Queries
**Date**: October 4, 2025  
**Purpose**: Evaluate all aspects of the multilingual tender RAG system

---

## 🎯 Test Categories

1. **Metadata Lookups** - Structured queries (DTAD-ID, year, region)
2. **Semantic Search** - Natural language understanding
3. **Multilingual Queries** - English & German
4. **Domain-Specific** - Tender/construction terminology
5. **Edge Cases** - Boundary testing
6. **Retrieval Quality** - Precision and relevance
7. **Answer Generation** - LLM quality
8. **Translation** - Cross-lingual accuracy

---

## 📋 CATEGORY 1: Metadata Lookups (Direct Answers)

### Test 1.1: Exact DTAD-ID Lookup
**Query**: `20046891`  
**Expected**: 
- Direct metadata answer
- DTAD-ID, title, date, region, contracting authority
- Source URL
- Response time: < 500ms

**What to Check**:
- ✅ Correct DTAD-ID in response
- ✅ All metadata fields present
- ✅ No hallucination

---

### Test 1.2: Different DTAD-ID
**Query**: `20046645`  
**Expected**: 
- Different tender details
- Verify accuracy against Test Data folder

---

### Test 1.3: DTAD-ID with Context
**Query**: `What is DTAD-ID 20047008 about?`  
**Expected**: 
- Metadata answer with description
- Natural language format

---

### Test 1.4: Multiple IDs (if applicable)
**Query**: `Show me information for 20046891 and 20046645`  
**Expected**: 
- Two separate results
- Or error message if not supported

---

## 📋 CATEGORY 2: Year & Region Filters

### Test 2.1: Year Filter
**Query**: `Show me all tenders from 2024`  
**Expected**: 
- List of 2024 tenders
- Top 5 results
- Each with DTAD-ID, title, date

**What to Check**:
- ✅ All dates are 2024
- ✅ No 2023 or 2025 results

---

### Test 2.2: Region Filter
**Query**: `tenders in Berlin`  
**Expected**: 
- List of Berlin-region tenders
- Metadata-based filtering

---

### Test 2.3: Year + Region Combined
**Query**: `Show me construction tenders from 2024 in Bavaria`  
**Expected**: 
- Filtered by both year and region
- Relevant results only

---

### Test 2.4: Invalid Year
**Query**: `tenders from 1990`  
**Expected**: 
- "Not in the tender data" or empty result
- No hallucination

---

## 📋 CATEGORY 3: Semantic Search (German Tenders)

### Test 3.1: General Construction Query
**Query**: `What are the requirements for road construction projects?`  
**Expected**: 
- 5-10 relevant chunks
- Citations [1], [2], etc.
- Scores > 0.5
- LLM answer summarizing requirements

**What to Check**:
- ✅ Chunks mention roads/construction
- ✅ Answer cites sources
- ✅ No off-topic results

---

### Test 3.2: Delivery & Timeline
**Query**: `What is the delivery deadline for tender 20046891?`  
**Expected**: 
- Specific date/timeline from documents
- Citation to source page
- Precise answer (no vague statements)

---

### Test 3.3: Budget & Pricing
**Query**: `What is the estimated budget for construction projects?`  
**Expected**: 
- Budget figures from documents
- Currency amounts with citations
- Multiple examples if available

---

### Test 3.4: Technical Specifications
**Query**: `What technical specifications are required for infrastructure projects?`  
**Expected**: 
- Technical details (materials, standards, etc.)
- Engineering requirements
- Compliance standards

---

### Test 3.5: Qualification Requirements
**Query**: `What qualifications do contractors need to participate in public tenders?`  
**Expected**: 
- Certification requirements
- Experience criteria
- Legal prerequisites

---

## 📋 CATEGORY 4: German Language Queries

### Test 4.1: Basic German Query
**Query**: `Welche Anforderungen gibt es für Straßenbauprojekte?`  
**Translation**: "What requirements exist for road construction projects?"

**Expected**: 
- German answer
- Citations [1], [2]
- Similar results to English Test 3.1

**What to Check**:
- ✅ Answer in German
- ✅ Same/similar chunks as English query
- ✅ Proper German grammar

---

### Test 4.2: Lieferfrist (Delivery Deadline)
**Query**: `Was ist die Lieferfrist für Ausschreibung 20046891?`  
**Translation**: "What is the delivery deadline for tender 20046891?"

**Expected**: 
- German answer with specific date
- Citation to source

---

### Test 4.3: Vergabestelle (Contracting Authority)
**Query**: `Welche Vergabestelle ist für dieses Projekt verantwortlich?`  
**Translation**: "Which contracting authority is responsible for this project?"

**Expected**: 
- Authority name from metadata or documents
- Contact information if available

---

### Test 4.4: Ausschreibung Details
**Query**: `Zeige mir Details zur Ausschreibung für Tiefbauarbeiten`  
**Translation**: "Show me details about the tender for civil engineering works"

**Expected**: 
- Multiple relevant tenders
- German descriptions
- Citations

---

### Test 4.5: Mixed Keywords
**Query**: `DTAD-ID 20046891 Lieferfrist und Budget`  
**Translation**: "DTAD-ID 20046891 delivery deadline and budget"

**Expected**: 
- Combined metadata and semantic search
- Both timeline and budget info

---

## 📋 CATEGORY 5: Domain-Specific Terminology

### Test 5.1: VOB (German Construction Contract)
**Query**: `What VOB regulations apply to these tenders?`  
**Expected**: 
- References to VOB/A, VOB/B, VOB/C
- Legal compliance requirements
- Or "Not in tender data" if not mentioned

---

### Test 5.2: DIN Standards
**Query**: `Which DIN standards are required?`  
**Expected**: 
- DIN standard numbers (e.g., DIN 18300)
- Technical specifications
- Compliance requirements

---

### Test 5.3: Honorarordnung (Fee Schedule)
**Query**: `What are the compensation terms according to HOAI?`  
**Expected**: 
- Fee schedule references
- Architect/engineer compensation
- Or not found if not in documents

---

### Test 5.4: Bauleistungen (Construction Services)
**Query**: `What types of Bauleistungen are included?`  
**Translation**: "What types of construction services are included?"

**Expected**: 
- Service categories
- Scope of work
- Detailed descriptions

---

## 📋 CATEGORY 6: Complex Multi-Part Queries

### Test 6.1: Multi-Criteria Search
**Query**: `Find tenders for road construction in 2024 with budget over 1 million euros`  
**Expected**: 
- Filtered by type, year, and budget
- Multiple criteria applied
- Top relevant results

---

### Test 6.2: Comparative Query
**Query**: `Compare requirements between tender 20046891 and 20046645`  
**Expected**: 
- Information from both tenders
- Side-by-side comparison
- Key differences highlighted

---

### Test 6.3: Temporal Query
**Query**: `What tenders are closing this week?`  
**Expected**: 
- Deadline-based filtering
- Current date awareness (Oct 4, 2025)
- Sorted by urgency

---

### Test 6.4: Geographic Range
**Query**: `Show me all tenders in southern Germany`  
**Expected**: 
- Bavaria, Baden-Württemberg results
- Geographic intelligence
- Regional grouping

---

## 📋 CATEGORY 7: Edge Cases & Boundary Testing

### Test 7.1: Empty Query
**Query**: `` (empty)  
**Expected**: 
- Error message or prompt
- No crash
- Helpful guidance

---

### Test 7.2: Very Long Query
**Query**: `I am looking for information about road construction projects that involve infrastructure development including highways autobahns bridges tunnels and other transportation related construction work that is currently being tendered or will be tendered soon in various regions of Germany with specific focus on technical requirements budget constraints delivery timelines qualification criteria for contractors and all relevant documentation needed to participate in the public procurement process` (500+ characters)

**Expected**: 
- Handles gracefully
- Returns relevant results
- No truncation errors

---

### Test 7.3: Special Characters
**Query**: `What about § 123 paragraph (2) clause [a-c]?`  
**Expected**: 
- Handles special chars correctly
- No parsing errors
- Relevant legal references

---

### Test 7.4: Numbers Only
**Query**: `2024 500000 Berlin`  
**Expected**: 
- Interprets as year, budget, location
- Returns relevant results

---

### Test 7.5: Non-Latin Script
**Query**: `Что такое тендер?` (Russian: "What is a tender?")  
**Expected**: 
- Detects unsupported language
- Graceful error or translation attempt
- No crash

---

### Test 7.6: SQL Injection Attempt (Security)
**Query**: `'; DROP TABLE tenders; --`  
**Expected**: 
- Treats as normal text
- No database errors
- Safe query processing

---

### Test 7.7: Malformed DTAD-ID
**Query**: `20046`  
**Expected**: 
- No match (too short)
- "Not in tender data"
- Suggests correct format

---

## 📋 CATEGORY 8: Off-Topic Queries (Grounding Test)

### Test 8.1: General Knowledge
**Query**: `What is the capital of France?`  
**Expected**: 
- ⚠️ "Not grounded" warning
- Fallback answer (Paris)
- Clear indicator this is NOT from tender data

---

### Test 8.2: Current Events
**Query**: `Who won the 2025 World Cup?`  
**Expected**: 
- "Not in tender data"
- Or general answer with grounding warning

---

### Test 8.3: Math Problem
**Query**: `What is 2 + 2?`  
**Expected**: 
- Simple answer (4)
- Grounding warning
- Or refusal to answer non-tender query

---

### Test 8.4: Tender-Related but Not in Data
**Query**: `What are the tender opportunities in France?`  
**Expected**: 
- "Not in tender data" (system has German tenders only)
- No hallucination
- Clear scope limitation

---

## 📋 CATEGORY 9: Conversation & Context

### Test 9.1: Follow-Up Question
**First Query**: `What is DTAD-ID 20046891 about?`  
**Follow-Up**: `What is the deadline?`  

**Expected**: 
- Uses context from first query
- Answers about 20046891 deadline
- No need to repeat DTAD-ID

---

### Test 9.2: Clarification
**First Query**: `construction tenders`  
**Follow-Up**: `I meant specifically road construction`  

**Expected**: 
- Refines previous search
- More specific results
- Context-aware

---

### Test 9.3: Multi-Turn Dialogue
1. `Show me tenders in Berlin`
2. `Which ones are for road construction?`
3. `What are the budgets?`
4. `When do they close?`

**Expected**: 
- Each question builds on previous
- Maintains conversation context
- Coherent responses

---

## 📋 CATEGORY 10: Translation Feature

### Test 10.1: German to English
**Steps**:
1. Ask: `Welche Anforderungen gibt es für Straßenbau?`
2. Get German answer
3. Click "🌐 Translate last answer"
4. Select "English"

**Expected**: 
- English translation
- Citations [1], [2] preserved
- Accurate translation

---

### Test 10.2: English to German
**Steps**:
1. Ask: `What are the road construction requirements?`
2. Get English answer
3. Click "🌐 Translate last answer"
4. Select "Deutsch"

**Expected**: 
- German translation
- Technical terms correct
- Natural German phrasing

---

### Test 10.3: Translation Consistency
**Test**: 
- Ask same question in English and German
- Compare answers
- Check if retrieved chunks are similar

**Expected**: 
- Dual-query mode finds same/similar documents
- Answers semantically equivalent
- Citation overlap

---

## 📋 CATEGORY 11: Source Verification

### Test 11.1: PDF Download
**Steps**:
1. Submit any query with results
2. Scroll to "Sources" section
3. Click "Download [1]" button

**Expected**: 
- PDF downloads successfully
- File opens correctly
- Page numbers match citations

---

### Test 11.2: Citation Accuracy
**Steps**:
1. Get answer with citations [1], [2]
2. Download source [1]
3. Navigate to cited page
4. Verify text matches

**Expected**: 
- Citation text appears on page
- Context is correct
- No false citations

---

### Test 11.3: Score Validation
**Query**: `road construction` (simple)  
**Expected**: 
- Top result score > 0.7 (high relevance)
- Score decreases down the list
- Scores > 0.5 for all top-5

---

## 📋 CATEGORY 12: Performance & Stress Testing

### Test 12.1: Response Time - Metadata
**Query**: `20046891`  
**Measure**: 
- Time from submit to answer
- Target: < 500ms

---

### Test 12.2: Response Time - Semantic
**Query**: `road construction requirements`  
**Measure**: 
- Time from submit to answer
- Target: < 5 seconds (including LLM)

---

### Test 12.3: Concurrent Queries
**Steps**:
1. Open 3 browser tabs
2. Submit different queries simultaneously

**Expected**: 
- All complete successfully
- No crashes
- Reasonable response times

---

### Test 12.4: Rapid Fire
**Steps**:
1. Submit query 1
2. Immediately submit query 2 (before 1 completes)
3. Check results

**Expected**: 
- Both queries handled
- No race conditions
- Correct results for each

---

## 📋 CATEGORY 13: UI/UX Testing

### Test 13.1: Settings Adjustment
**Steps**:
1. Change Top-K to 5
2. Submit query
3. Count results

**Expected**: 
- Exactly 5 sources shown
- Setting applies immediately

---

### Test 13.2: Temperature Effect
**Steps**:
1. Set temperature to 0.0
2. Ask: `Summarize tender requirements`
3. Set temperature to 1.0
4. Ask same question

**Expected**: 
- Temp 0.0: More factual, deterministic
- Temp 1.0: More creative, varied

---

### Test 13.3: History Management
**Steps**:
1. Ask 3 questions
2. Click "🧹 Clear history"
3. Check chat area

**Expected**: 
- All messages cleared
- Clean slate
- No memory of previous queries

---

### Test 13.4: Export Chat
**Steps**:
1. Have some conversation
2. Click "⬇️ Export chat (.md)"
3. Download file
4. Open in text editor

**Expected**: 
- Markdown format
- All messages included
- Readable formatting

---

### Test 13.5: Debug Mode
**Steps**:
1. Enable "Show retrieved chunks"
2. Submit query
3. Check output

**Expected**: 
- Raw chunk text visible
- Scores displayed
- Useful for debugging

---

## 📋 CATEGORY 14: Error Handling

### Test 14.1: Qdrant Down
**Steps**:
1. Stop Qdrant container: `docker stop qdrant`
2. Submit query

**Expected**: 
- Graceful error message
- No crash
- Guidance to check Qdrant

*(Restart Qdrant: `docker start qdrant`)*

---

### Test 14.2: Ollama Down
**Steps**:
1. Stop Ollama
2. Submit query

**Expected**: 
- Retrieval still works
- LLM error message shown
- Fallback behavior

---

### Test 14.3: Missing PDF
**Steps**:
1. Find query that references deleted/moved PDF
2. Try to download

**Expected**: 
- "Missing file" button (disabled)
- Error message
- No crash

---

### Test 14.4: Invalid Model
**Steps**:
1. In sidebar, if you can select model
2. Try non-existent model

**Expected**: 
- Error message
- Fallback to default
- Or validation prevents selection

---

## 📊 EVALUATION SCORECARD

After testing, rate each category:

| Category | Pass/Fail | Score (1-5) | Notes |
|----------|-----------|-------------|-------|
| Metadata Lookups | | | |
| Year/Region Filters | | | |
| Semantic Search | | | |
| German Queries | | | |
| Domain Terms | | | |
| Complex Queries | | | |
| Edge Cases | | | |
| Grounding Test | | | |
| Conversation Context | | | |
| Translation | | | |
| Source Verification | | | |
| Performance | | | |
| UI/UX | | | |
| Error Handling | | | |

**Overall Score**: _____ / 70

---

## 🎯 Success Criteria

### ✅ System is Production-Ready if:
- [ ] 90%+ of metadata queries return correct results
- [ ] 80%+ of semantic queries are relevant
- [ ] German and English queries work equally well
- [ ] Grounding detection works (flags off-topic queries)
- [ ] Citations are accurate (spot check 10+ sources)
- [ ] Translation preserves meaning
- [ ] Response time < 10 seconds for 95% of queries
- [ ] No crashes during testing
- [ ] Error handling is graceful
- [ ] UI is intuitive and responsive

---

## 🚀 Quick Test Suite (10 Minutes)

If you're short on time, run these **10 essential tests**:

1. ✅ `20046891` (metadata)
2. ✅ `road construction requirements` (semantic EN)
3. ✅ `Welche Anforderungen für Straßenbau?` (semantic DE)
4. ✅ `tenders from 2024` (year filter)
5. ✅ `What is the capital of France?` (grounding)
6. ✅ Follow-up test (ask one, then clarify)
7. ✅ Download a PDF source
8. ✅ Translate an answer
9. ✅ Empty query (edge case)
10. ✅ Check response times

---

## 📝 Sample Expected Outputs

### Example 1: DTAD-ID Query
```
Query: 20046891

Expected Output:
"DTAD-ID 20046891 | Titel: [Project Title] | Datum: 2024-XX-XX | 
Region: [Region Name] | Vergabestelle: [Authority Name] | 
Quelle: [Source URL]"
```

### Example 2: Semantic Query
```
Query: What are the requirements for road construction?

Expected Output:
"Based on the tender documents, road construction projects require:

1. Technical specifications according to DIN standards [1]
2. Qualified contractors with experience in infrastructure [2]
3. Compliance with VOB regulations [3]
4. Environmental impact assessments [4]

Sources:
[1] Tender 20046xxx, Page 12 (Score: 0.85)
[2] Tender 20047xxx, Page 8 (Score: 0.78)
..."
```

### Example 3: German Query
```
Query: Welche Anforderungen gibt es für Straßenbau?

Expected Output:
"Gemäß den Ausschreibungsunterlagen sind folgende Anforderungen erforderlich:

1. Technische Spezifikationen nach DIN-Normen [1]
2. Qualifizierte Auftragnehmer mit Erfahrung im Tiefbau [2]
3. VOB-konforme Ausführung [3]
...
```

---

**Good luck with your testing! 🚀**

This comprehensive suite should help you evaluate every aspect of your RAG system. Start with the Quick Test Suite, then dive deeper into specific categories as needed.
