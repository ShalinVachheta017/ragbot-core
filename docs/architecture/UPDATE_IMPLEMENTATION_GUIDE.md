# 🔄 Complete Update & Implementation Plan

## Overview
This guide shows you how to update your RAG system with:
1. ✅ **Option A**: Directory Reorganization
2. ✅ **Option B**: FastAPI Backend
3. ✅ **Option C**: Knowledge Graph
4. ✅ **Option D**: RAGAS Evaluation + Guardrails
5. ✅ **All Options**: Complete transformation

---

## 📦 Option A: Directory Reorganization (30 minutes)

### Step 1: Create New Directory Structure

```powershell
# Create new folder structure
cd d:\Projects\multilingual-ragbot

# Main source code
New-Item -ItemType Directory -Path "src\api\routes" -Force
New-Item -ItemType Directory -Path "src\api\models" -Force
New-Item -ItemType Directory -Path "src\api\middleware" -Force
New-Item -ItemType Directory -Path "src\knowledge_graph" -Force
New-Item -ItemType Directory -Path "src\reranker" -Force
New-Item -ItemType Directory -Path "src\monitoring" -Force
New-Item -ItemType Directory -Path "src\guardrails" -Force
New-Item -ItemType Directory -Path "src\utils" -Force

# Reorganize UI
New-Item -ItemType Directory -Path "ui\streamlit\components" -Force
New-Item -ItemType Directory -Path "ui\streamlit\pages" -Force

# Scripts reorganization
New-Item -ItemType Directory -Path "scripts\data_processing" -Force
New-Item -ItemType Directory -Path "scripts\knowledge_graph" -Force
New-Item -ItemType Directory -Path "scripts\evaluation" -Force
New-Item -ItemType Directory -Path "scripts\deployment" -Force

# Testing
New-Item -ItemType Directory -Path "tests\unit" -Force
New-Item -ItemType Directory -Path "tests\integration" -Force
New-Item -ItemType Directory -Path "tests\e2e" -Force

# Evaluation
New-Item -ItemType Directory -Path "evaluation\datasets" -Force
New-Item -ItemType Directory -Path "evaluation\metrics" -Force
New-Item -ItemType Directory -Path "evaluation\reports" -Force

# Documentation reorganization
New-Item -ItemType Directory -Path "docs\architecture" -Force
New-Item -ItemType Directory -Path "docs\guides" -Force
New-Item -ItemType Directory -Path "docs\development" -Force
New-Item -ItemType Directory -Path "docs\research" -Force

# Configs
New-Item -ItemType Directory -Path "configs" -Force

# Docker
New-Item -ItemType Directory -Path "docker" -Force

# Notebooks
New-Item -ItemType Directory -Path "notebooks" -Force
```

### Step 2: Move Files to New Structure

```powershell
# Move core files to src/core
Move-Item -Path "core\*" -Destination "src\core\" -Force

# Move UI files
Move-Item -Path "ui\app_streamlit.py" -Destination "ui\streamlit\app.py" -Force

# Move scripts
Move-Item -Path "scripts\parse_excel.py" -Destination "scripts\data_processing\" -Force
Move-Item -Path "scripts\embed.py" -Destination "scripts\data_processing\" -Force
Move-Item -Path "scripts\ingest.py" -Destination "scripts\data_processing\" -Force
Move-Item -Path "scripts\build_bm25_index.py" -Destination "scripts\deployment\" -Force
Move-Item -Path "scripts\validate_hybrid.py" -Destination "scripts\evaluation\" -Force

# Move documentation to organized folders
Move-Item -Path "BASELINE_ANALYSIS.md" -Destination "docs\research\" -Force
Move-Item -Path "HYBRID_SEARCH_FIX.md" -Destination "docs\research\" -Force
Move-Item -Path "HYBRID_SEARCH_IMPLEMENTATION.md" -Destination "docs\research\" -Force
Move-Item -Path "EVALUATION_STRATEGY.md" -Destination "docs\research\" -Force
Move-Item -Path "IMPLEMENTATION_PLAN.md" -Destination "docs\development\" -Force
Move-Item -Path "FILE_AUDIT.md" -Destination "docs\development\" -Force
Move-Item -Path "VERIFICATION_REPORT.md" -Destination "docs\development\" -Force
Move-Item -Path "SAMPLE_QUERIES.md" -Destination "evaluation\datasets\" -Force

Move-Item -Path "QUICKSTART.md" -Destination "docs\guides\" -Force
Move-Item -Path "PRODUCTION_GUIDE.md" -Destination "docs\guides\" -Force
Move-Item -Path "INTERVIEW_PREP_GUIDE.md" -Destination "docs\guides\" -Force

# Keep README.md at root
# Keep docker-compose.yml at root
# Keep requirements.txt at root
# Keep pyproject.toml at root
```

### Step 3: Update Import Paths

```powershell
# You'll need to update imports in all Python files
# Old: from core.config import ...
# New: from src.core.config import ...

# This can be done with a script or manually
```

### Step 4: Create __init__.py Files

```powershell
# Make all directories Python packages
New-Item -ItemType File -Path "src\__init__.py" -Force
New-Item -ItemType File -Path "src\api\__init__.py" -Force
New-Item -ItemType File -Path "src\api\routes\__init__.py" -Force
New-Item -ItemType File -Path "src\api\models\__init__.py" -Force
New-Item -ItemType File -Path "src\api\middleware\__init__.py" -Force
New-Item -ItemType File -Path "src\core\__init__.py" -Force
New-Item -ItemType File -Path "src\knowledge_graph\__init__.py" -Force
New-Item -ItemType File -Path "src\reranker\__init__.py" -Force
New-Item -ItemType File -Path "src\monitoring\__init__.py" -Force
New-Item -ItemType File -Path "src\guardrails\__init__.py" -Force
New-Item -ItemType File -Path "src\utils\__init__.py" -Force
```

---

## 🚀 Option B: FastAPI Backend (2-3 days)

### Step 1: Install Dependencies

```powershell
pip install fastapi>=0.104.0
pip install uvicorn[standard]>=0.24.0
pip install python-jose[cryptography]  # JWT auth
pip install passlib[bcrypt]  # Password hashing
pip install python-multipart  # Form data
pip install redis>=5.0.0  # Caching
pip install prometheus-client>=0.18.0  # Metrics
```

### Step 2: Create FastAPI Main Application

Create `src/api/main.py`:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

# Import routes
from src.api.routes import search, health, admin

# Create FastAPI app
app = FastAPI(
    title="RAG Tender Search API",
    description="Production-ready RAG API for German tender documents",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

@app.get("/")
async def root():
    return {
        "message": "RAG Tender Search API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 3: Create Pydantic Models

Create `src/api/models/requests.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    top_k: int = Field(8, ge=1, le=50, description="Number of results")
    use_hybrid: bool = Field(True, description="Use hybrid search")
    use_reranker: bool = Field(False, description="Use cross-encoder reranking")
    filters: Optional[dict] = Field(None, description="Metadata filters")

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(8, ge=1, le=50)
    conversation_history: Optional[List[dict]] = Field(None)

class FeedbackRequest(BaseModel):
    query_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None
```

Create `src/api/models/responses.py`:

```python
from pydantic import BaseModel
from typing import List, Optional, Dict

class Source(BaseModel):
    text: str
    metadata: Dict
    score: float

class SearchResponse(BaseModel):
    query: str
    results: List[Source]
    total_found: int
    processing_time: float

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: float
    query_id: str
    processing_time: float
```

### Step 4: Create Search Endpoints

Create `src/api/routes/search.py`:

```python
from fastapi import APIRouter, HTTPException, Depends
from src.api.models.requests import SearchRequest, ChatRequest
from src.api.models.responses import SearchResponse, ChatResponse
from src.core.search import search_hybrid, search_dense
from src.core.qa import answer_question
from src.guardrails.custom import RAGGuardrails
import time
import uuid

router = APIRouter()
guardrails = RAGGuardrails()

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Semantic search endpoint.
    
    Returns top-K most relevant document chunks.
    """
    start_time = time.time()
    
    # Input validation with guardrails
    is_safe, error_msg = guardrails.check_input(request.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Perform search
        if request.use_hybrid:
            results = search_hybrid(
                query=request.query,
                top_k=request.top_k,
                filters=request.filters
            )
        else:
            results = search_dense(
                query=request.query,
                top_k=request.top_k,
                filters=request.filters
            )
        
        processing_time = time.time() - start_time
        
        return SearchResponse(
            query=request.query,
            results=[
                {
                    "text": r.text,
                    "metadata": r.metadata,
                    "score": r.score
                }
                for r in results
            ],
            total_found=len(results),
            processing_time=processing_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Conversational Q&A endpoint.
    
    Returns generated answer with citations.
    """
    start_time = time.time()
    query_id = str(uuid.uuid4())
    
    # Input validation
    is_safe, error_msg = guardrails.check_input(request.question)
    if not is_safe:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Retrieve contexts
        contexts = search_hybrid(request.question, top_k=request.top_k)
        
        # Apply context guardrails
        safe_contexts = guardrails.check_contexts([c.text for c in contexts])
        
        # Generate answer
        answer = answer_question(request.question, safe_contexts)
        
        # Output guardrails
        is_safe, error_msg = guardrails.check_output(answer, safe_contexts)
        if not is_safe:
            answer = error_msg
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            answer=answer,
            sources=[
                {
                    "text": c.text,
                    "metadata": c.metadata,
                    "score": c.score
                }
                for c in contexts
            ],
            confidence=0.85,  # Calculate actual confidence
            query_id=query_id,
            processing_time=processing_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback for query."""
    # Store feedback in database for RLHF
    return {"status": "success", "message": "Feedback recorded"}
```

### Step 5: Create Health Endpoints

Create `src/api/routes/health.py`:

```python
from fastapi import APIRouter
import time

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with dependencies."""
    # Check Qdrant
    try:
        # Test Qdrant connection
        qdrant_status = "healthy"
    except:
        qdrant_status = "unhealthy"
    
    # Check Ollama
    try:
        # Test Ollama connection
        ollama_status = "healthy"
    except:
        ollama_status = "unhealthy"
    
    return {
        "status": "healthy" if all([
            qdrant_status == "healthy",
            ollama_status == "healthy"
        ]) else "degraded",
        "services": {
            "qdrant": qdrant_status,
            "ollama": ollama_status
        },
        "timestamp": time.time()
    }
```

### Step 6: Run FastAPI Server

```powershell
# Development mode (with hot reload)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Access API docs at: http://localhost:8000/api/docs
```

---

## 🕸️ Option C: Knowledge Graph (3-4 days)

### Step 1: Install Dependencies

```powershell
pip install networkx>=3.2  # Lightweight graph library
pip install spacy>=3.7.0  # NER
pip install matplotlib>=3.8.0  # Visualization
pip install pyvis>=0.3.2  # Interactive graph viz

# Download German NER model
python -m spacy download de_core_news_lg
```

### Step 2: Create Knowledge Graph Builder

Create `src/knowledge_graph/builder.py`:

```python
import networkx as nx
import spacy
from typing import List, Dict, Tuple
import json
import pickle

class TenderKnowledgeGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.nlp = spacy.load("de_core_news_lg")
    
    def extract_entities(self, text: str, metadata: Dict) -> List[Tuple]:
        """Extract entities from tender document."""
        doc = self.nlp(text)
        
        entities = []
        
        # Extract from spaCy NER
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'LOC', 'GPE', 'PERSON']:
                entities.append((ent.text, ent.label_))
        
        # Extract from metadata
        dtad_id = metadata.get('dtad_id')
        cpv_codes = metadata.get('cpv_codes', [])
        region = metadata.get('region')
        date = metadata.get('publication_date')
        
        return entities, dtad_id, cpv_codes, region, date
    
    def build_from_documents(self, documents: List[Dict]):
        """Build KG from all tender documents."""
        
        for doc in documents:
            text = doc['text']
            metadata = doc['metadata']
            
            # Extract entities
            entities, dtad_id, cpv_codes, region, date = self.extract_entities(text, metadata)
            
            # Add tender node
            self.graph.add_node(
                dtad_id,
                type='tender',
                text=text[:200],  # Preview
                date=date
            )
            
            # Add CPV code nodes and relationships
            for cpv in cpv_codes:
                self.graph.add_node(cpv, type='cpv_code')
                self.graph.add_edge(dtad_id, cpv, relation='has_cpv')
            
            # Add region node
            if region:
                self.graph.add_node(region, type='region')
                self.graph.add_edge(dtad_id, region, relation='located_in')
            
            # Add organization nodes
            for ent_text, ent_type in entities:
                if ent_type == 'ORG':
                    self.graph.add_node(ent_text, type='organization')
                    self.graph.add_edge(dtad_id, ent_text, relation='issued_by')
                elif ent_type in ['LOC', 'GPE']:
                    self.graph.add_node(ent_text, type='location')
                    self.graph.add_edge(dtad_id, ent_text, relation='mentions')
        
        print(f"Built KG with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
    
    def save(self, path: str):
        """Save KG to disk."""
        with open(path, 'wb') as f:
            pickle.dump(self.graph, f)
    
    def load(self, path: str):
        """Load KG from disk."""
        with open(path, 'rb') as f:
            self.graph = pickle.load(f)
```

### Step 3: Create KG Query Module

Create `src/knowledge_graph/query.py`:

```python
import networkx as nx
from typing import List, Dict

class KnowledgeGraphQuery:
    def __init__(self, kg: nx.MultiDiGraph):
        self.kg = kg
    
    def find_related_tenders(self, dtad_id: str, max_hops: int = 2) -> List[str]:
        """Find tenders related through graph connections."""
        if dtad_id not in self.kg:
            return []
        
        # Find all nodes within max_hops
        related = []
        for node in self.kg.nodes():
            if node == dtad_id:
                continue
            if self.kg.nodes[node].get('type') == 'tender':
                # Check if there's a path
                try:
                    path_length = nx.shortest_path_length(self.kg, dtad_id, node)
                    if path_length <= max_hops:
                        related.append(node)
                except nx.NetworkXNoPath:
                    continue
        
        return related
    
    def find_by_region(self, region: str) -> List[str]:
        """Find all tenders in a specific region."""
        tenders = []
        for node in self.kg.nodes():
            if self.kg.nodes[node].get('type') == 'tender':
                # Check if connected to region
                for neighbor in self.kg.neighbors(node):
                    if neighbor == region:
                        tenders.append(node)
        return tenders
    
    def find_by_cpv(self, cpv_code: str) -> List[str]:
        """Find all tenders with specific CPV code."""
        if cpv_code not in self.kg:
            return []
        
        # Find all tenders connected to this CPV
        tenders = []
        for predecessor in self.kg.predecessors(cpv_code):
            if self.kg.nodes[predecessor].get('type') == 'tender':
                tenders.append(predecessor)
        return tenders
    
    def expand_query(self, entities: List[str]) -> List[str]:
        """Expand query entities using graph relationships."""
        expanded = set(entities)
        
        for entity in entities:
            if entity in self.kg:
                # Add direct neighbors
                for neighbor in self.kg.neighbors(entity):
                    expanded.add(neighbor)
        
        return list(expanded)
```

### Step 4: Enhance RAG with KG

Create `src/knowledge_graph/enhancer.py`:

```python
from src.knowledge_graph.query import KnowledgeGraphQuery
from src.core.search import search_hybrid
import spacy

class KGEnhancedRetrieval:
    def __init__(self, kg_query: KnowledgeGraphQuery):
        self.kg_query = kg_query
        self.nlp = spacy.load("de_core_news_lg")
    
    def search_with_kg(self, query: str, top_k: int = 8):
        """Search using both vector search and KG."""
        
        # 1. Extract entities from query
        doc = self.nlp(query)
        entities = [ent.text for ent in doc.ents]
        
        # 2. Expand query using KG
        expanded_entities = self.kg_query.expand_query(entities)
        
        # 3. Find candidate tenders from KG
        kg_candidates = set()
        for entity in expanded_entities:
            # Check if it's a region
            region_tenders = self.kg_query.find_by_region(entity)
            kg_candidates.update(region_tenders)
            
            # Check if it's a CPV code
            cpv_tenders = self.kg_query.find_by_cpv(entity)
            kg_candidates.update(cpv_tenders)
        
        # 4. Perform hybrid search
        search_results = search_hybrid(query, top_k=top_k * 2)
        
        # 5. Boost results that appear in KG candidates
        boosted_results = []
        for result in search_results:
            dtad_id = result.metadata.get('dtad_id')
            if dtad_id in kg_candidates:
                result.score *= 1.5  # Boost score by 50%
            boosted_results.append(result)
        
        # 6. Re-sort and return top-K
        boosted_results.sort(key=lambda x: x.score, reverse=True)
        return boosted_results[:top_k]
```

### Step 5: Build the KG

Create `scripts/knowledge_graph/build_kg.py`:

```python
from src.knowledge_graph.builder import TenderKnowledgeGraph
from qdrant_client import QdrantClient

# Initialize
kg = TenderKnowledgeGraph()
client = QdrantClient(url="http://localhost:6333")

# Get all documents from Qdrant
collection_name = "tender_docs_jina-v3_d1024_fresh"
offset = None
all_docs = []

while True:
    results = client.scroll(
        collection_name=collection_name,
        limit=100,
        offset=offset
    )
    
    points = results[0]
    if not points:
        break
    
    for point in points:
        all_docs.append({
            'text': point.payload.get('text', ''),
            'metadata': point.payload
        })
    
    offset = results[1]
    if offset is None:
        break

print(f"Loaded {len(all_docs)} documents")

# Build KG
kg.build_from_documents(all_docs)

# Save KG
kg.save('data/state/tender_knowledge_graph.pkl')
print("Knowledge Graph saved!")
```

### Step 6: Run KG Builder

```powershell
python scripts/knowledge_graph/build_kg.py
```

---

## 🧪 Option D: RAGAS Evaluation + Guardrails (2-3 days)

### Step 1: Install Dependencies

```powershell
pip install ragas>=0.1.0
pip install datasets>=2.15.0
pip install presidio-analyzer>=2.2.0
pip install presidio-anonymizer>=2.2.0
pip install detoxify>=0.5.0
```

### Step 2: Prepare Test Dataset

Create `evaluation/datasets/test_queries.json`:

```json
[
  {
    "question": "Was ist DTAD-ID 20046891?",
    "expected_answer": "Tender for IT services...",
    "category": "direct_lookup"
  },
  {
    "question": "Show me tenders in Dresden",
    "expected_answer": "List of Dresden tenders...",
    "category": "geographic"
  },
  {
    "question": "IT-Projekte tenders",
    "expected_answer": "IT project tenders...",
    "category": "keyword_search"
  }
]
```

### Step 3: Run RAGAS Evaluation

Create `scripts/evaluation/run_ragas.py`:

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevance, context_precision
from datasets import Dataset
import json
from src.core.qa import answer_question
from src.core.search import search_hybrid

# Load test queries
with open('evaluation/datasets/test_queries.json') as f:
    test_data = json.load(f)

# Generate responses
results = []
for item in test_data:
    query = item['question']
    
    # Get contexts
    contexts = search_hybrid(query, top_k=8)
    context_texts = [c.text for c in contexts]
    
    # Generate answer
    answer = answer_question(query, context_texts)
    
    results.append({
        'question': query,
        'answer': answer,
        'contexts': [context_texts],
        'ground_truth': item.get('expected_answer', '')
    })

# Create dataset
dataset = Dataset.from_dict({
    'question': [r['question'] for r in results],
    'answer': [r['answer'] for r in results],
    'contexts': [r['contexts'] for r in results],
    'ground_truth': [r['ground_truth'] for r in results]
})

# Evaluate
scores = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevance, context_precision]
)

print("RAGAS Evaluation Results:")
print(f"Faithfulness: {scores['faithfulness']:.3f}")
print(f"Answer Relevance: {scores['answer_relevance']:.3f}")
print(f"Context Precision: {scores['context_precision']:.3f}")
```

### Step 4: Implement Guardrails

See `docs/guides/EVALUATION_AND_SAFETY_GUIDE.md` for complete implementation!

---

## ✅ Complete Update Checklist

### Week 1
- [ ] Reorganize directory structure
- [ ] Update all import paths
- [ ] Create FastAPI skeleton
- [ ] Implement basic search endpoints
- [ ] Set up RAGAS evaluation

### Week 2
- [ ] Build Knowledge Graph
- [ ] Integrate KG with RAG
- [ ] Implement guardrails
- [ ] Add cross-encoder reranker
- [ ] Create evaluation reports

### Week 3
- [ ] Add monitoring dashboard
- [ ] Write comprehensive docs
- [ ] Create demo video
- [ ] Prepare for interview

---

## 🚀 Quick Start Commands

```powershell
# 1. Reorganize (run all commands from above)

# 2. Install all dependencies
pip install -r requirements.txt
pip install fastapi uvicorn[standard] python-jose passlib redis prometheus-client
pip install ragas datasets presidio-analyzer presidio-anonymizer detoxify
pip install networkx spacy matplotlib pyvis
python -m spacy download de_core_news_lg

# 3. Build Knowledge Graph
python scripts/knowledge_graph/build_kg.py

# 4. Run evaluation
python scripts/evaluation/run_ragas.py

# 5. Start FastAPI
uvicorn src.api.main:app --reload --port 8000

# 6. Start Streamlit (parallel)
streamlit run ui/streamlit/app.py --server.port 8501
```

---

## 🎯 What to Show in Interview

1. **Clean Architecture** - "Organized project structure with src/, tests/, evaluation/"
2. **FastAPI** - "Production REST API with OpenAPI docs at /api/docs"
3. **Knowledge Graph** - "Graph-enhanced retrieval with entity relationships"
4. **RAGAS Evaluation** - "Automated evaluation with faithfulness, relevance metrics"
5. **Guardrails** - "Safety checks for hallucinations, PII, toxicity"
6. **Monitoring** - "Prometheus metrics, response time tracking"

**This is a SENIOR-LEVEL RAG system!** 🚀
