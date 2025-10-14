"""
Hybrid Search: BM25 (sparse keyword) + Dense (vector) fusion for better exact-match retrieval.

This module provides:
- BM25 indexing of tender documents
- BM25 search functionality
- Reciprocal Rank Fusion (RRF) to combine BM25 + dense results
"""
from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from rank_bm25 import BM25Okapi

from .config import CFG


# ─── German stopwords (common words to filter out) ─────────────────────────
GERMAN_STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines",
    "und", "oder", "aber", "ist", "sind", "wird", "werden", "hat", "haben",
    "für", "von", "mit", "auf", "in", "zu", "an", "bei", "durch", "über",
    "um", "nach", "aus", "vor", "zwischen", "unter", "auch", "noch", "nur",
    "sich", "nicht", "mehr", "als", "wie", "da", "so", "wenn", "dann",
}


# ─── Simple tokenizer ───────────────────────────────────────────────────────
def tokenize_german(text: str) -> List[str]:
    """
    Simple German tokenizer:
    - Lowercases
    - Splits on whitespace and punctuation
    - Removes stopwords
    - Keeps alphanumeric tokens (≥2 chars)
    """
    text = text.lower()
    # Split on non-alphanumeric (keeps digits)
    tokens = re.findall(r'\w+', text)
    # Filter stopwords and very short tokens
    return [t for t in tokens if len(t) >= 2 and t not in GERMAN_STOPWORDS]


# ─── BM25 Index Class ───────────────────────────────────────────────────────
class BM25Index:
    """
    BM25 sparse retrieval index.
    
    Attributes:
        bm25: BM25Okapi instance
        doc_ids: List of document IDs (Qdrant point IDs)
        doc_metadata: Dict mapping doc_id -> metadata (for debugging/filtering)
    """
    
    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.doc_ids: List[str] = []
        self.doc_metadata: Dict[str, Dict] = {}
        self._is_built = False
    
    def build_index(self, documents: List[Dict]) -> None:
        """
        Build BM25 index from documents.
        
        Args:
            documents: List of dicts with keys:
                - 'id': str (Qdrant point ID)
                - 'text': str (document text to index)
                - 'metadata': dict (optional, for filtering/debugging)
        """
        if not documents:
            raise ValueError("Cannot build BM25 index with empty document list")
        
        print(f"🔨 Building BM25 index from {len(documents)} documents...")
        
        # Tokenize all documents
        tokenized_docs = []
        self.doc_ids = []
        self.doc_metadata = {}
        
        for doc in documents:
            doc_id = str(doc['id'])
            text = doc.get('text', '')
            
            if not text:
                print(f"⚠️  Warning: Document {doc_id} has no text, skipping")
                continue
            
            tokens = tokenize_german(text)
            if not tokens:
                print(f"⚠️  Warning: Document {doc_id} tokenized to empty, skipping")
                continue
            
            tokenized_docs.append(tokens)
            self.doc_ids.append(doc_id)
            self.doc_metadata[doc_id] = doc.get('metadata', {})
        
        if not tokenized_docs:
            raise ValueError("No valid documents to index (all empty after tokenization)")
        
        # Build BM25 index
        self.bm25 = BM25Okapi(tokenized_docs)
        self._is_built = True
        
        print(f"✅ BM25 index built with {len(self.doc_ids)} documents")
    
    def search(self, query: str, top_k: int = 100) -> List[Tuple[str, float]]:
        """
        Search BM25 index with query.
        
        Args:
            query: Search query string
            top_k: Number of results to return
        
        Returns:
            List of (doc_id, score) tuples, sorted by score descending
        """
        if not self._is_built or self.bm25 is None:
            raise RuntimeError("BM25 index not built. Call build_index() first.")
        
        # Tokenize query
        query_tokens = tokenize_german(query)
        
        if not query_tokens:
            # Empty query after tokenization
            return []
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Sort by score and return top_k
        scored_docs = [(self.doc_ids[i], float(scores[i])) 
                      for i in range(len(scores))]
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return scored_docs[:top_k]
    
    def save(self, filepath: Path) -> None:
        """Save BM25 index to disk."""
        if not self._is_built:
            raise RuntimeError("Cannot save: index not built")
        
        data = {
            'bm25': self.bm25,
            'doc_ids': self.doc_ids,
            'doc_metadata': self.doc_metadata,
        }
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"💾 BM25 index saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: Path) -> 'BM25Index':
        """Load BM25 index from disk."""
        if not filepath.exists():
            raise FileNotFoundError(f"BM25 index not found at {filepath}")
        
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        index = cls()
        index.bm25 = data['bm25']
        index.doc_ids = data['doc_ids']
        index.doc_metadata = data['doc_metadata']
        index._is_built = True
        
        print(f"📂 BM25 index loaded from {filepath} ({len(index.doc_ids)} docs)")
        return index


# ─── Global BM25 index singleton ────────────────────────────────────────────
_bm25_index: Optional[BM25Index] = None


def get_bm25_index() -> BM25Index:
    """
    Get or load the global BM25 index.
    
    Returns:
        BM25Index instance
    
    Raises:
        RuntimeError: If index file doesn't exist
    """
    global _bm25_index
    
    if _bm25_index is None:
        index_path = CFG.state_dir / "bm25_index.pkl"
        
        if not index_path.exists():
            raise RuntimeError(
                f"BM25 index not found at {index_path}. "
                "Run 'python scripts/build_bm25_index.py' to create it."
            )
        
        _bm25_index = BM25Index.load(index_path)
    
    return _bm25_index


def reload_bm25_index() -> None:
    """Force reload of BM25 index (useful after rebuilding)."""
    global _bm25_index
    _bm25_index = None
    get_bm25_index()


# ─── Reciprocal Rank Fusion ─────────────────────────────────────────────────
def reciprocal_rank_fusion(
    result_sets: List[List[Tuple[str, float]]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """
    Reciprocal Rank Fusion (RRF) to combine multiple ranked lists.
    
    Args:
        result_sets: List of ranked lists, each containing (doc_id, score) tuples
        k: RRF constant (default: 60, standard value from literature)
    
    Returns:
        Fused list of (doc_id, fused_score) tuples, sorted by fused_score descending
    
    Reference:
        Cormack et al. "Reciprocal Rank Fusion outperforms Condorcet and 
        individual Rank Learning Methods" (SIGIR 2009)
    """
    fused_scores: Dict[str, float] = {}
    
    for results in result_sets:
        for rank, (doc_id, _) in enumerate(results, start=1):
            # RRF formula: score = 1 / (k + rank)
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (k + rank))
    
    # Sort by fused score descending
    fused_results = [(doc_id, score) for doc_id, score in fused_scores.items()]
    fused_results.sort(key=lambda x: x[1], reverse=True)
    
    return fused_results


# ─── Hybrid Search Function ─────────────────────────────────────────────────
def search_bm25(query: str, top_k: int = 100) -> List[Tuple[str, float]]:
    """
    Perform BM25 sparse search.
    
    Args:
        query: Search query
        top_k: Number of results to return
    
    Returns:
        List of (doc_id, bm25_score) tuples
    """
    index = get_bm25_index()
    return index.search(query, top_k=top_k)

