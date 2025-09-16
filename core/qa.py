# core/qa.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np
import torch
import re
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from FlagEmbedding import FlagReranker
import requests
from pathlib import Path
import fitz
from .config import CFG

@dataclass
class Hit:
    text: str
    score: float
    payload: Dict

class DenseRetriever:
    def __init__(self, cfg=CFG):
        self.cfg = cfg
        
        # 🔧 FIX: Properly define device
        if torch.cuda.is_available():
            device = 'cuda'
        else:
            device = 'cpu'
            
        # 🔧 FIX: Initialize embedder with device
        self.embedder = SentenceTransformer(
            cfg.embed_model, 
            device=device, 
            trust_remote_code=True
        )
        
        # 🔧 FIX: Enable FP16 for GPU
        if device == 'cuda':
            self.embedder = self.embedder.half()
        
        # 🔧 FIX: Initialize Qdrant client
        self.client = QdrantClient(
            url=cfg.qdrant_url,
            grpc_port=6334,
            prefer_grpc=True
        )

    def _cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def _encode_query(self, q: str) -> np.ndarray:
        # 🔧 FIX: Use self.embedder instead of self.model
        v = self.embedder.encode([q], normalize_embeddings=True)
        embedded = np.asarray(v, dtype="float32")[0]
        
        # 🔧 FIX: Crop to configured dimension (512 for Matryoshka)
        if len(embedded) > self.cfg.embed_dim:
            embedded = embedded[:self.cfg.embed_dim]
            
        return embedded

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

class Reranker:
    """🆕 NEW: BGE reranker for precision boost"""
    def __init__(self, model_name: str, weight: float = 0.8, bs: int = 64):
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.m = FlagReranker(model_name, use_fp16=(dev=="cuda"), device=dev)
        self.w = weight
        self.bs = bs

    def _clip(self, txt: str, max_chars: int = 1800) -> str:
        return txt[:max_chars] if len(txt) > max_chars else txt

    def rerank(self, query: str, hits: List[Hit], keep: int) -> List[Hit]:
        if len(hits) <= keep:
            return hits

        # Get text content for reranking
        texts = [(h.text or h.payload.get("text","")) for h in hits]
        pairs = [[query, self._clip(t)] for t in texts]

        # Compute reranker scores
        scores = self.m.compute_score(pairs, batch_size=self.bs, normalize=True)

        # Blend dense + rerank scores
        merged = []
        for h, s in zip(hits, scores):
            blended_score = self.w * float(s) + (1-self.w) * float(h.score)
            merged.append(Hit(
                text=h.text,
                score=blended_score,
                payload=h.payload
            ))

        return sorted(merged, key=lambda x: x.score, reverse=True)[:keep]

class SparseRetriever:
    """Tiny local TF-IDF that ranks payload text"""
    def __init__(self, corpus: List[str] | None = None):
        self.vec = TfidfVectorizer(max_features=50000)
        self.corpus = corpus or []
        self.X = self.vec.fit_transform(self.corpus) if self.corpus else None

    def search(self, query: str, top_k: int) -> List[Hit]:
        if self.X is None:
            return []
        qv = self.vec.transform([query])
        scores = (self.X @ qv.T).toarray().ravel()
        idx = np.argsort(-scores)[:top_k]
        return [Hit(text=self.corpus[i], score=float(scores[i]), payload={}) for i in idx]

class HybridRetriever:
    def __init__(self, dense: DenseRetriever, sparse: Optional[SparseRetriever] = None):
        self.dense, self.sparse = dense, sparse

    def search(self, query: str, top_k: int) -> List[Hit]:
        d = self.dense.search(query, top_k=top_k)
        s = self.sparse.search(query, top_k=top_k) if self.sparse else []

        # RRF fusion
        def rrf(hits: List[Hit]) -> Dict[str, float]:
            scores = {}
            for rank, h in enumerate(hits, start=1):
                key = h.payload.get("source_path","") + f"#{h.payload.get('chunk_idx',-1)}"
                scores[key] = scores.get(key, 0.0) + 1.0/(60.0 + rank)
            return scores

        score_map = rrf(d)
        if s:
            sparse_scores = rrf(s)
            for key, score in sparse_scores.items():
                score_map[key] = score_map.get(key, 0.0) + score

        merged = []
        for h in d:
            key = h.payload.get("source_path","") + f"#{h.payload.get('chunk_idx',-1)}"
            merged.append(Hit(text=h.text, score=score_map.get(key, h.score), payload=h.payload))

        return sorted(merged, key=lambda x: x.score, reverse=True)[:top_k]

class Answerer:
    """LLM wrapper with on-demand PDF text loading"""
    def __init__(self, cfg=CFG):
        self.cfg = cfg

    def _load_pages_text(self, source_path: str, p_start: int | None, p_end: int | None, max_chars: int = 1200) -> str:
        """Load text from PDF pages on-demand when payload text is missing"""
        if not source_path or p_start is None or p_end is None:
            return ""

        try:
            # Handle null/empty source_path
            if source_path == "null":
                return "[Source path missing from index]"

            p = Path(source_path)
            # If absolute path doesn't exist, try relative to extract dir
            if not p.exists():
                extract_dir = Path("data/extract")
                p = extract_dir / p.name  # Just filename

            if not p.exists():
                return f"[File not found: {p.name}]"

            with fitz.open(p) as doc:
                p_start = max(1, int(p_start))
                p_end = min(len(doc), int(p_end))
                texts = []
                for i in range(p_start-1, p_end):
                    if i < len(doc):
                        page_text = doc[i].get_text() or ""
                        texts.append(page_text)

                out = "\n".join(texts).strip()
                return out[:max_chars] + ("..." if len(out) > max_chars else "")

        except Exception as e:
            return f"[Error loading PDF: {e}]"

    def answer(self, query: str, hits: List[Hit]) -> str:
        blocks = []
        for h in hits[:self.cfg.final_k]:
            pl = h.payload or {}
            src = pl.get("source_path", "")
            ps, pe = pl.get("page_start"), pl.get("page_end")

            # Build clean citation with just filename
            cite = f"[{Path(src).name}:p{ps}-{pe}]" if (ps is not None and pe is not None) else f"[{Path(src).name}]"

            # Try to get text content (payload first, then on-demand loading)
            snippet = (h.text or pl.get("text", "")).strip()
            if not snippet:
                snippet = self._load_pages_text(src, ps, pe)

            if snippet and snippet != "[No text content available]":
                blocks.append(f"{cite}\n{snippet}")
            else:
                blocks.append(f"{cite}\n[No readable text content]")

        context = "\n\n---\n\n".join(blocks) if blocks else "(no context)"
        prompt = (
            "Answer the user using ONLY the context provided. If the information is not present, say you don't know. "
            "Respond in German if the question is in German. Be specific and cite sources.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\nAnswer:"
        )

        return _ask_llm(prompt)

def _should_skip_rerank(query: str) -> bool:
    """Skip reranking for deterministic ID lookups"""
    return bool(re.match(r'^\d{8}$', query.strip()))  # DTAD-ID pattern

def retrieve_candidates(query: str, cfg=CFG) -> List[Hit]:
    """🔧 UPDATED: Now with reranker integration"""
    dense = DenseRetriever(cfg)
    sparse = SparseRetriever() if cfg.use_hybrid else None
    retr = HybridRetriever(dense=dense, sparse=sparse)

    hits = retr.search(query, top_k=cfg.topk_candidate)

    # Apply reranker if enabled and beneficial
    if cfg.use_rerank and hits and not _should_skip_rerank(query):
        rr = Reranker(cfg.reranker_model, weight=cfg.rerank_weight, bs=cfg.rerank_batch_size)
        # Ensure text content is available for reranking
        for h in hits:
            if not h.text:
                h.text = h.payload.get("text", "")
        hits = rr.rerank(query, hits, keep=cfg.rerank_keep)

    return hits

def answer_query(query: str, cfg=CFG) -> str:
    hits = retrieve_candidates(query, cfg)
    ans = Answerer(cfg).answer(query, hits)
    return ans

def _ask_llm(prompt: str) -> str:
    """LLM call with Ollama fallback to direct API"""
    # Try Ollama Python client first
    try:
        import ollama
        response = ollama.chat(
            model=CFG.llm_model,
            messages=[{"role": "user", "content": prompt}],
            options={
                "num_predict": 256,
                "temperature": 0.2,
                "top_p": 0.9
            }
        )
        return response["message"]["content"].strip()
    
    except Exception as ollama_error:
        # Fallback to direct HTTP API
        try:
            body = {
                "model": CFG.llm_model,
                "prompt": prompt,
                "options": {"num_predict": 256, "temperature": 0.2},
                "stream": False,
            }

            r = requests.post("http://localhost:11434/api/generate", json=body, timeout=60)
            r.raise_for_status()
            data = r.json()
            response = (data.get("response") or "").strip()
            return response or "[LLM returned empty response]"
        
        except Exception as api_error:
            return f"[LLM unavailable - Ollama: {ollama_error}, API: {api_error}] Based on the context, I found relevant documents but cannot generate an answer."
