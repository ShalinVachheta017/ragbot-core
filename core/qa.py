# core/qa.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
import requests
from .config import CFG

@dataclass
class Hit:
    text: str
    score: float
    payload: Dict

class DenseRetriever:
    def __init__(self, cfg=CFG):
        self.cfg = cfg
        self.client = QdrantClient(url=cfg.qdrant_url)
        self.model = SentenceTransformer(cfg.embed_model, device="cuda" if self._cuda() else "cpu")

    def _cuda(self) -> bool:
        try:
            import torch; return torch.cuda.is_available()
        except Exception:
            return False

    def _encode_query(self, q: str) -> np.ndarray:
        v = self.model.encode([f"query: {q}"], normalize_embeddings=True)
        return np.asarray(v, dtype="float32")[0]

    def search(self, query: str, top_k: int) -> List[Hit]:
        v = self._encode_query(query)
        res = self.client.search(
            collection_name=self.cfg.qdrant_collection,
            query_vector=v.tolist(),
            limit=top_k,
            with_payload=True,
            search_params=models.SearchParams(hnsw_ef=self.cfg.hnsw_ef_search, exact=False),
        )
        hits: List[Hit] = []
        for r in res:
            if r.score is None or r.score < self.cfg.min_score:
                continue
            pl = r.payload or {}
            txt = pl.get("text", "")  # use chunk text if stored during indexing
            hits.append(Hit(text=txt, score=float(r.score), payload=pl))
        return hits

    def __init__(self, cfg=CFG):
        self.cfg = cfg
        self.client = QdrantClient(url=cfg.qdrant_url)
        self.model = SentenceTransformer(cfg.embed_model, device="cuda" if self._cuda() else "cpu")
    def _cuda(self) -> bool:
        try:
            import torch; return torch.cuda.is_available()
        except Exception: return False
    def _encode_query(self, q: str) -> np.ndarray:
        v = self.model.encode([f"query: {q}"], normalize_embeddings=True)
        return np.asarray(v, dtype="float32")[0]
    def search(self, query: str, top_k: int) -> List[Hit]:
        v = self._encode_query(query)
        res = self.client.search(
            collection_name=self.cfg.qdrant_collection,
            query_vector=v.tolist(),
            limit=top_k,
            with_payload=True,
            search_params=models.SearchParams(hnsw_ef=self.cfg.hnsw_ef_search, exact=False),
        )
        return [Hit(text="", score=r.score, payload=r.payload) for r in res]

class SparseRetriever:
    """Tiny local TF-IDF that ranks payload text (requires we stored text; if not, skip or load text on demand)."""
    def __init__(self, corpus: List[str] | None = None):
        self.vec = TfidfVectorizer(max_features=50000)
        self.corpus = corpus or []
        self.X = self.vec.fit_transform(self.corpus) if self.corpus else None
    def search(self, query: str, top_k: int) -> List[Hit]:
        if self.X is None: return []
        qv = self.vec.transform([query])
        scores = (self.X @ qv.T).toarray().ravel()
        idx = np.argsort(-scores)[:top_k]
        return [Hit(text=self.corpus[i], score=float(scores[i]), payload={}) for i in idx]

class HybridRetriever:
    def __init__(self, dense: DenseRetriever, sparse: Optional[SparseRetriever]=None):
        self.dense, self.sparse = dense, sparse
    def search(self, query: str, top_k: int) -> List[Hit]:
        d = self.dense.search(query, top_k=top_k)
        s = self.sparse.search(query, top_k=top_k) if self.sparse else []
        # RRF fusion (simple)
        def rrf(hits: List[Hit]) -> Dict[str, float]:
            ranks, scores = {}, {}
            for rank, h in enumerate(hits, start=1):
                key = h.payload.get("source_path","") + f"#{h.payload.get('chunk_idx',-1)}"
                scores[key] = scores.get(key, 0.0) + 1.0/(60.0 + rank)  # rrf_k=60
                ranks[key] = rank
            return scores
        score_map = rrf(d)
        if s: 
            for rank, h in enumerate(s, start=1):
                key = h.payload.get("source_path","") + f"#{h.payload.get('chunk_idx',-1)}"
                score_map[key] = score_map.get(key, 0.0) + 1.0/(60.0 + rank)
        # produce merged list using dense payloads as base
        merged = []
        for h in d:
            key = h.payload.get("source_path","") + f"#{h.payload.get('chunk_idx',-1)}"
            merged.append(Hit(text=h.text, score=score_map.get(key, h.score), payload=h.payload))
        return sorted(merged, key=lambda x: x.score, reverse=True)[:top_k]

class Answerer:
    """LLM wrapper; expects top-k chunks in payload or loads text by path."""
    def __init__(self, cfg=CFG):
        self.cfg = cfg
    def answer(self, query: str, hits: List[Hit]) -> str:
        context_lines = []
        for h in hits[: self.cfg.final_k]:
            src = h.payload.get("source_path", "")
            pg  = h.payload.get("page", None)
            context_lines.append(f"[{src}{f':p{pg}' if pg is not None else ''}]")
        prompt = (
            "Answer the user using ONLY the context. If not present, say you don't know.\n\n"
            f"Context:\n" + "\n".join(context_lines) + "\n\n"
            f"Question: {query}\nAnswer:"
        )
        # Ollama call (pseudo; wire your existing code)
        try:
            import ollama
            r = ollama.chat(model=self.cfg.llm_model, messages=[{"role":"user","content":prompt}], options={"num_predict":256})
            return r["message"]["content"]
        except Exception:
            return "(LLM unavailable) " + prompt

def retrieve_candidates(query: str, cfg=CFG) -> List[Hit]:
    dense = DenseRetriever(cfg)
    # if you build a sparse corpus later, instantiate SparseRetriever(corpus)
    retr = HybridRetriever(dense=dense, sparse=None if not cfg.use_hybrid else None)
    return retr.search(query, top_k=cfg.topk_candidate)

def answer_query(query: str, cfg=CFG) -> str:
    hits = retrieve_candidates(query, cfg)
    ans = Answerer(cfg).answer(query, hits)
    return ans

def _ask_llm(prompt: str) -> str:
    body = {
        "model": CFG.llm_model,
        "prompt": prompt,
        "options": {"num_predict": 256, "temperature": 0.2},
        "stream": False,
    }
    r = requests.post("http://localhost:11434/api/generate", json=body, timeout=180)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip() or "[LLM returned empty response]"
