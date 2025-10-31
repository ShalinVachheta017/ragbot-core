# 🧪 RAG Evaluation & Safety Guide

## Table of Contents
1. [RAG Evaluation Overview](#rag-evaluation-overview)
2. [RAGAS Framework](#ragas-framework)
3. [Guardrails for AI Safety](#guardrails-for-ai-safety)
4. [Implementation Guide](#implementation-guide)

---

## 📊 RAG Evaluation Overview

### Why Evaluate RAG Systems?

RAG has **3 components** to evaluate:
```
Query → [Retrieval] → Retrieved Chunks → [Generation] → Answer
         ↑ Evaluate          ↑ Evaluate         ↑ Evaluate
```

### Evaluation Categories

#### 1️⃣ **Retrieval Quality** (Did we get the right documents?)
- **Hit Rate@K** - Was relevant doc in top K results?
- **MRR (Mean Reciprocal Rank)** - How high was the first relevant doc?
- **Precision@K** - What % of top K are relevant?
- **Recall@K** - What % of all relevant docs did we retrieve?
- **NDCG** - Quality score considering ranking position

#### 2️⃣ **Generation Quality** (Is the answer good?)
- **Faithfulness** - Is answer grounded in retrieved context?
- **Answer Relevance** - Does answer match the question?
- **Context Relevance** - Are retrieved chunks useful?
- **Correctness** - Is the answer factually correct?

#### 3️⃣ **End-to-End Quality**
- **User Satisfaction** - Thumbs up/down feedback
- **Task Success Rate** - Did user find what they needed?
- **Response Time** - How fast is the system?

---

## 🎯 RAGAS Framework

### What is RAGAS?

**RAGAS** = **R**etrieval **A**ugmented **G**eneration **A**ssessment **S**ystem

It's a **framework for evaluating RAG pipelines** WITHOUT needing human-labeled ground truth!

### Key Insight: LLM-as-a-Judge 🤖

RAGAS uses an **LLM (GPT-4, Claude)** to judge the quality of:
- Retrieved contexts
- Generated answers
- Relevance to questions

### RAGAS Metrics Explained

#### 1. **Faithfulness** (Hallucination Detection)
```
Question: "What is the tender budget?"
Context: "The tender has a budget of €500,000"
Answer: "The budget is €500,000" → ✅ Faithful
Answer: "The budget is €1 million" → ❌ Hallucination
```

**How it works:**
1. Extract claims from the answer
2. Check if each claim is supported by context
3. Faithfulness = (supported claims) / (total claims)

#### 2. **Answer Relevance**
```
Question: "What is the deadline?"
Answer: "The deadline is December 31, 2024" → ✅ Relevant
Answer: "The tender is in Dresden..." → ❌ Off-topic
```

**How it works:**
1. LLM generates questions from the answer
2. Compare similarity to original question
3. High similarity = relevant answer

#### 3. **Context Precision**
```
Question: "What are the CPV codes?"
Contexts:
  [1] "CPV: 45000000 - Construction work" → ✅ Relevant
  [2] "The tender was published in 2024" → ❌ Irrelevant
  [3] "CPV: 71000000 - Engineering" → ✅ Relevant
```

**Measures:** Are relevant contexts ranked higher?

#### 4. **Context Recall**
```
Ground Truth: "Deadline is Dec 31, attributed to clause 3.2"
Retrieved Context: "Deadline is Dec 31" (has deadline but missing clause)
Context Recall: 0.5 (only 50% of info retrieved)
```

**Measures:** Did we retrieve all necessary info?

#### 5. **Context Relevance**
```
Retrieved 10 chunks, but only 3 are relevant
Context Relevance = 3/10 = 0.3
```

**Measures:** Signal-to-noise ratio

---

## 🛡️ Guardrails for AI Safety

### What are Guardrails?

**Guardrails** = Safety checks to prevent:
- ❌ Harmful/toxic outputs
- ❌ Hallucinations
- ❌ PII leakage (personal data)
- ❌ Jailbreak attempts
- ❌ Off-topic responses

### Guardrails Framework (NeMo Guardrails)

**NeMo Guardrails** by NVIDIA is the leading framework for RAG safety.

#### Types of Guardrails

**1. Input Guardrails** (Before LLM)
```python
# Check user input for:
- Jailbreak attempts ("Ignore previous instructions...")
- Toxic language
- PII in query
- Off-topic questions
```

**2. Retrieval Guardrails**
```python
# Check retrieved docs for:
- PII in context (mask before sending to LLM)
- Irrelevant/low-quality chunks
- Malicious content
```

**3. Output Guardrails** (After LLM)
```python
# Check LLM response for:
- Hallucinations (not grounded in context)
- Toxic/harmful content
- PII leakage
- Off-topic answers
```

### Example Guardrails

#### 1. **Hallucination Detection**
```python
def check_faithfulness(answer, context):
    # Extract claims from answer
    claims = extract_claims(answer)
    
    # Check each claim against context
    supported = sum(is_in_context(claim, context) for claim in claims)
    faithfulness_score = supported / len(claims)
    
    if faithfulness_score < 0.7:
        return "I don't have enough information to answer that."
```

#### 2. **PII Masking**
```python
def mask_pii(text):
    # Detect and mask:
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)  # SSN
    text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]', text)  # Email
    text = re.sub(r'\b\d{10}\b', '[PHONE]', text)  # Phone
    return text
```

#### 3. **Topic Filtering**
```python
def is_on_topic(query, allowed_topics=["tender", "procurement", "contract"]):
    # Check if query is about tenders
    intent = classify_intent(query)
    if intent not in allowed_topics:
        return False, "I can only answer questions about tender documents."
    return True, None
```

#### 4. **Toxicity Filter**
```python
from detoxify import Detoxify

def check_toxicity(text):
    results = Detoxify('original').predict(text)
    if results['toxicity'] > 0.7:
        return True, "Response contains inappropriate content"
    return False, None
```

---

## 🚀 Implementation Guide

### Step 1: Install Dependencies

```bash
# Evaluation
pip install ragas>=0.1.0
pip install langchain>=0.1.0

# Guardrails
pip install nemoguardrails>=0.5.0
pip install detoxify  # Toxicity detection
pip install presidio-analyzer presidio-anonymizer  # PII detection
```

### Step 2: Set Up RAGAS Evaluation

```python
# evaluation/ragas_eval.py

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevance,
    context_precision,
    context_recall,
    context_relevancy
)
from datasets import Dataset

# Prepare evaluation dataset
data = {
    "question": [
        "What is DTAD-ID 20046891?",
        "Show me tenders in Dresden",
        # ... more test queries
    ],
    "answer": [
        # Generated answers from your RAG
    ],
    "contexts": [
        # List of retrieved contexts for each query
        [["context 1", "context 2", ...]],
    ],
    "ground_truth": [
        # (Optional) Expected answers
        "Tender for IT services in Dresden..."
    ]
}

dataset = Dataset.from_dict(data)

# Evaluate
result = evaluate(
    dataset,
    metrics=[
        faithfulness,
        answer_relevance,
        context_precision,
        context_recall,
        context_relevancy
    ]
)

print(result)
# Output:
# {
#   'faithfulness': 0.92,
#   'answer_relevance': 0.87,
#   'context_precision': 0.78,
#   'context_recall': 0.85,
#   'context_relevancy': 0.81
# }
```

### Step 3: Set Up Guardrails

```python
# src/guardrails/safety.py

from nemoguardrails import RailsConfig, LLMRails

# Define guardrails config
config = RailsConfig.from_content(
    yaml_content="""
    models:
      - type: main
        engine: ollama
        model: qwen2.5:1.5b
    
    rails:
      input:
        flows:
          - check jailbreak attempts
          - check off-topic queries
          - detect PII in input
      
      retrieval:
        flows:
          - filter irrelevant contexts
          - mask PII in contexts
      
      output:
        flows:
          - check hallucinations
          - verify answer is grounded
          - check for toxic content
          - prevent PII leakage
    """,
    
    colang_content="""
    # Input Guardrails
    define user ask off-topic
      "How do I make a bomb?"
      "Tell me a joke"
      "What's the weather?"
    
    define flow check off-topic
      user ask off-topic
      bot inform cannot help with that
    
    # Output Guardrails  
    define bot inform cannot help with that
      "I can only answer questions about tender documents."
    
    define bot answer faithfully
      bot answer based on context
      bot cite sources
    """
)

# Initialize guardrails
rails = LLMRails(config)

# Use in your RAG pipeline
def safe_qa(question, context):
    # Apply guardrails
    response = rails.generate(
        messages=[{
            "role": "user",
            "content": question
        }],
        context={
            "retrieved_contexts": context
        }
    )
    return response
```

### Step 4: Implement Custom Guardrails

```python
# src/guardrails/custom.py

import re
from typing import Tuple, Optional
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

class RAGGuardrails:
    def __init__(self):
        self.pii_analyzer = AnalyzerEngine()
        self.pii_anonymizer = AnonymizerEngine()
    
    def check_input(self, query: str) -> Tuple[bool, Optional[str]]:
        """Check if input query is safe."""
        
        # 1. Check for jailbreak attempts
        jailbreak_patterns = [
            r"ignore previous instructions",
            r"disregard all",
            r"pretend you are",
            r"roleplay as",
        ]
        if any(re.search(p, query.lower()) for p in jailbreak_patterns):
            return False, "Invalid query format."
        
        # 2. Check if on-topic
        tender_keywords = ["tender", "vergabe", "ausschreibung", "dtad", "cpv", "contract"]
        if not any(kw in query.lower() for kw in tender_keywords):
            return False, "I can only answer questions about tender documents."
        
        # 3. Mask PII in query
        pii_results = self.pii_analyzer.analyze(text=query, language='en')
        if pii_results:
            query = self.pii_anonymizer.anonymize(text=query, analyzer_results=pii_results)
        
        return True, None
    
    def check_contexts(self, contexts: list[str]) -> list[str]:
        """Filter and mask contexts."""
        
        # 1. Mask PII in contexts
        safe_contexts = []
        for ctx in contexts:
            pii_results = self.pii_analyzer.analyze(text=ctx, language='de')
            if pii_results:
                ctx = self.pii_anonymizer.anonymize(text=ctx, analyzer_results=pii_results).text
            safe_contexts.append(ctx)
        
        return safe_contexts
    
    def check_output(self, answer: str, contexts: list[str]) -> Tuple[bool, Optional[str]]:
        """Check if output is safe and faithful."""
        
        # 1. Check faithfulness (simplified)
        # Extract key facts from answer
        answer_lower = answer.lower()
        
        # Check if answer references context
        if "not found" in answer_lower or "no information" in answer_lower:
            return True, None  # Honest "don't know"
        
        # 2. Check for common hallucination patterns
        hallucination_patterns = [
            r"according to my knowledge",
            r"based on what I know",
            r"in general",  # Too generic
        ]
        if any(re.search(p, answer_lower) for p in hallucination_patterns):
            return False, "I don't have enough information in the tender documents to answer that."
        
        # 3. Check if answer has citations
        if not re.search(r'\[\d+\]', answer):
            return False, "Unable to cite sources for this answer."
        
        # 4. Mask any PII in output
        pii_results = self.pii_analyzer.analyze(text=answer, language='de')
        if pii_results:
            answer = self.pii_anonymizer.anonymize(text=answer, analyzer_results=pii_results).text
        
        return True, None
```

### Step 5: Integrate into Your RAG Pipeline

```python
# src/core/safe_qa.py

from src.guardrails.custom import RAGGuardrails
from src.core.qa import answer_question

class SafeRAGPipeline:
    def __init__(self):
        self.guardrails = RAGGuardrails()
    
    def query(self, question: str, top_k: int = 8):
        """Safe RAG pipeline with guardrails."""
        
        # 1. Input guardrails
        is_safe, error_msg = self.guardrails.check_input(question)
        if not is_safe:
            return {
                "answer": error_msg,
                "sources": [],
                "blocked": True
            }
        
        # 2. Retrieve contexts
        contexts = self.retrieve(question, top_k)
        
        # 3. Context guardrails (mask PII)
        safe_contexts = self.guardrails.check_contexts(contexts)
        
        # 4. Generate answer
        answer = answer_question(question, safe_contexts)
        
        # 5. Output guardrails
        is_safe, error_msg = self.guardrails.check_output(answer, safe_contexts)
        if not is_safe:
            return {
                "answer": error_msg,
                "sources": [],
                "blocked": True
            }
        
        return {
            "answer": answer,
            "sources": safe_contexts,
            "blocked": False
        }
```

---

## 📊 Complete Evaluation Pipeline

```python
# evaluation/comprehensive_eval.py

import pandas as pd
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevance, context_precision
from datasets import Dataset

class RAGEvaluator:
    def __init__(self, test_queries_path: str):
        self.test_queries = pd.read_json(test_queries_path)
    
    def run_evaluation(self):
        """Run comprehensive evaluation."""
        
        results = []
        
        for _, row in self.test_queries.iterrows():
            query = row['question']
            
            # Get RAG response
            response = self.rag_pipeline.query(query)
            
            results.append({
                'question': query,
                'answer': response['answer'],
                'contexts': [response['sources']],
                'ground_truth': row.get('expected_answer', ''),
                'category': row.get('category', 'general')
            })
        
        # Create dataset
        dataset = Dataset.from_dict({
            'question': [r['question'] for r in results],
            'answer': [r['answer'] for r in results],
            'contexts': [r['contexts'] for r in results],
            'ground_truth': [r['ground_truth'] for r in results]
        })
        
        # Evaluate with RAGAS
        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevance, context_precision]
        )
        
        # Create report
        report = pd.DataFrame(results)
        report['faithfulness'] = scores['faithfulness']
        report['answer_relevance'] = scores['answer_relevance']
        report['context_precision'] = scores['context_precision']
        
        # Save results
        report.to_csv('evaluation/reports/ragas_evaluation.csv', index=False)
        
        # Print summary
        print("\n=== RAGAS Evaluation Results ===")
        print(f"Faithfulness: {scores['faithfulness']:.3f}")
        print(f"Answer Relevance: {scores['answer_relevance']:.3f}")
        print(f"Context Precision: {scores['context_precision']:.3f}")
        
        # Breakdown by category
        print("\n=== Results by Category ===")
        for category in report['category'].unique():
            cat_data = report[report['category'] == category]
            print(f"\n{category.upper()}:")
            print(f"  Faithfulness: {cat_data['faithfulness'].mean():.3f}")
            print(f"  Answer Relevance: {cat_data['answer_relevance'].mean():.3f}")
            print(f"  Context Precision: {cat_data['context_precision'].mean():.3f}")
        
        return report

# Run evaluation
if __name__ == "__main__":
    evaluator = RAGEvaluator('evaluation/datasets/test_queries.json')
    results = evaluator.run_evaluation()
```

---

## 🎯 What to Implement for Your Project

### ✅ **Must Have** (Week 1)

1. **Basic RAGAS Evaluation**
   - Test with your 87 queries from `SAMPLE_QUERIES.md`
   - Measure: Faithfulness, Answer Relevance, Context Precision
   - Generate evaluation report

2. **Simple Guardrails**
   - Input: Check if query is about tenders
   - Output: Check for citations (hallucination prevention)
   - PII masking (emails, phone numbers)

### ⭐ **Should Have** (Week 2)

3. **Comprehensive Evaluation**
   - Add retrieval metrics (Hit Rate, MRR)
   - Break down by query category
   - Compare Dense vs Hybrid vs KG-enhanced

4. **Advanced Guardrails**
   - Jailbreak detection
   - Toxicity filtering
   - Full Presidio PII detection

### 🚀 **Nice to Have** (Week 3)

5. **Continuous Evaluation**
   - Log all queries for offline evaluation
   - A/B testing framework
   - Real-time monitoring dashboard

6. **Production Safety**
   - Rate limiting
   - Query caching
   - Error tracking

---

## 📈 Interview Talking Points

### RAGAS
- **"I use RAGAS for evaluation"** - Shows you know industry standards
- **"LLM-as-a-judge"** - Scalable evaluation without manual labeling
- **"Measuring faithfulness"** - Preventing hallucinations

### Guardrails
- **"I implement input/output guardrails"** - Shows safety awareness
- **"PII protection with Presidio"** - Data privacy compliance
- **"Jailbreak prevention"** - Security mindset

### Complete System
- **"End-to-end evaluation pipeline"** - Data-driven development
- **"Safety by design"** - Not an afterthought
- **"Production-ready with monitoring"** - Enterprise mindset

---

## 🚀 Next Steps

1. **Install RAGAS** and run first evaluation
2. **Implement basic guardrails** (input/output checks)
3. **Create test dataset** from SAMPLE_QUERIES.md
4. **Generate evaluation report** with scores

**Want me to help you implement any of these?** 🎯
