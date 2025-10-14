# core/qa.py
from .config import CFG
from .search import search_dense, search_hybrid, rrf  # we'll fuse multi-query results via RRFom __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

import requests
import fitz  # PyMuPDF

from langdetect import detect
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from .config import CFG
from .search import search_dense, rrf  # we’ll fuse multi-query results via RRF

# Optional reranker (BAAI/bge-reranker-v2-m3)
try:
    from FlagEmbedding import FlagReranker
    _HAS_RERANKER = True
except Exception:
    _HAS_RERANKER = False


# ----------------------------- Data types ------------------------------------

@dataclass
class Hit:
    text: str
    score: float
    payload: Dict[str, Any]
    page: Optional[int] = None
    source: str = ""


# ---------------------------- Utilities --------------------------------------

def _translate_to_de(text: str) -> str:
    """
    Best-effort EN→DE translation via Ollama (qwen2.5). If unavailable, returns input.
    """
    try:
        import ollama
        prompt = (
            "Übersetze exakt ins Deutsche. Erhalte Namen, Zahlen, Fachbegriffe. "
            "Nicht zusammenfassen oder umformulieren.\n\nTEXT:\n" + text + "\n\nDEUTSCH:"
        )
        out = ollama.chat(model=CFG.llm_model, messages=[{"role": "user", "content": prompt}])
        return out["message"]["content"].strip()
    except Exception:
        return text


def _assert_dims_match_once() -> None:
    """
    Fast-fail if someone switched the model or collection to a different dimension.
    Skips check if collection doesn't exist yet.
    """
    try:
        m = SentenceTransformer(CFG.embed_model, trust_remote_code=True)
        dim = m.get_sentence_embedding_dimension()
        client = QdrantClient(url=CFG.qdrant_url)
        
        # Check if collection exists before trying to access it
        if not client.collection_exists(CFG.qdrant_collection):
            import logging
            logger = logging.getLogger("core.qa")
            logger.warning(f"Qdrant collection '{CFG.qdrant_collection}' does not exist yet. Skipping dimension check.")
            return
            
        vecs = client.get_collection(CFG.qdrant_collection).config.params.vectors
        qdim = vecs.size if hasattr(vecs, "size") else list(vecs.values())[0].size
        if dim != qdim:
            raise RuntimeError(f"Embedding dim mismatch: model={dim}, qdrant={qdim}")
    except Exception as e:
        import logging
        logger = logging.getLogger("core.qa")
        logger.warning(f"Could not verify embedding dimensions: {e}")


_assert_dims_match_once()


def _sp_to_hit(sp) -> Hit:
    pl = sp.payload or {}
    txt = (pl.get("text") or pl.get("chunk_text") or "")[:2000]
    src = pl.get("source_path") or pl.get("source") or ""
    page = pl.get("page_start") or pl.get("page")
    return Hit(text=txt, score=float(sp.score or 0.0), payload=pl, page=page, source=src)


def _should_skip_rerank(query: str) -> bool:
    """
    Skip reranking for deterministic ID lookups (e.g., 8-digit DTAD-ID).
    """
    return bool(re.fullmatch(r"\d{8}", query.strip()))


# ---------------------------- Public API -------------------------------------

def retrieve_candidates(user_text: str, cfg=CFG, limit: Optional[int] = None) -> List[Hit]:
    """
    Retrieves candidates using:
      - Hybrid search (BM25 + dense) if cfg.use_hybrid is True
      - Dense-only otherwise
      
    Optional multilingual routing:
      - multilingual default (no translation), OR
      - DE-only routing (translate then search), OR
      - dual retrieval (original + DE) fused via RRF.
      
    Optional BGE reranking if enabled and available.
    """
    limit = int(limit or cfg.top_k)

    # Language detect (best-effort)
    try:
        lang = detect(user_text)
    except Exception:
        lang = "de"

    # Choose search method (hybrid or dense)
    search_fn = search_hybrid if cfg.use_hybrid else search_dense

    # Strategy selection
    if not cfg.force_german_retrieval and not cfg.dual_query:
        res = search_fn(user_text, limit)
    elif cfg.force_german_retrieval and not cfg.dual_query:
        de_q = user_text if lang == "de" else _translate_to_de(user_text)
        res = search_fn(de_q, limit)
    else:
        # Dual retrieval + RRF fusion
        res_en = search_fn(user_text, limit)
        de_q   = user_text if lang == "de" else _translate_to_de(user_text)
        res_de = search_fn(de_q, limit)
        res    = rrf([res_en, res_de])[:limit]

    hits = [_sp_to_hit(r) for r in res]

    # Optional reranking
    if cfg.use_rerank and _HAS_RERANKER and hits and not _should_skip_rerank(user_text):
        try:
            reranker = FlagReranker(cfg.reranker_model, use_fp16=True)
            # make sure we have text for each item
            pairs = [(user_text, (h.text or h.payload.get("text", ""))[:1800]) for h in hits]
            scores = reranker.compute_score(pairs, normalize=True)
            blended: List[Tuple[float, Hit]] = []
            w = float(cfg.rerank_weight)
            for h, s in zip(hits, scores):
                blended.append((w * float(s) + (1.0 - w) * float(h.score), h))
            blended.sort(key=lambda t: t[0], reverse=True)
            keep = int(cfg.rerank_keep)
            hits = [h for _, h in blended[:keep]]
        except Exception:
            pass

    # Final cut (maps to cfg.final_k so the UI stays snappy)
    return hits[: int(cfg.final_k)]


def answer_query(user_text: str, cfg=CFG) -> str:
    """
    Minimal answerer: stitches snippets from top hits and asks the LLM.
    Replace with your preferred prompting if you want.
    """
    hits = retrieve_candidates(user_text, cfg)
    blocks: List[str] = []
    for h in hits[: int(cfg.final_k)]:
        pl = h.payload or {}
        src = pl.get("source_path", "") or pl.get("source", "")
        ps, pe = pl.get("page_start"), pl.get("page_end")
        cite = f"[{Path(src).name}:p{ps}-{pe}]" if (ps is not None and pe is not None) else f"[{Path(src).name or 'source'}]"
        snippet = (h.text or pl.get("text", "")).strip()
        if not snippet:
            snippet = _load_pages_text(src, ps, pe)
        blocks.append(f"{cite}\n{snippet or '[No readable text]'}")

    context = "\n\n---\n\n".join(blocks) if blocks else "(no context)"
    prompt = (
        "Beantworte die Frage NUR mit dem bereitgestellten Kontext. "
        "Wenn es nicht im Kontext steht, sage ehrlich, dass du es nicht weißt. "
        "Antworte auf Deutsch, wenn die Frage Deutsch ist; sonst antworte in der Sprache der Frage. "
        "Sei präzise und nenne die Quelle in eckigen Klammern.\n\n"
        f"Kontext:\n{context}\n\nFrage: {user_text}\nAntwort:"
    )
    return _ask_llm(prompt)


# ----------------------- PDF fallback & LLM bridge ---------------------------

def _load_pages_text(source_path: str, p_start: Optional[int], p_end: Optional[int], max_chars: int = 1200) -> str:
    if not source_path or p_start is None or p_end is None:
        return ""
    try:
        p = Path(source_path)
        if not p.exists():
            # fallback to extract_dir/filename.pdf
            p = Path(CFG.extract_dir) / p.name
        if not p.exists():
            return f"[File not found: {Path(source_path).name}]"

        with fitz.open(p) as doc:
            p_start = max(1, int(p_start))
            p_end = min(len(doc), int(p_end))
            texts = []
            for i in range(p_start - 1, p_end):
                texts.append(doc[i].get_text() or "")
            out = "\n".join(texts).strip()
            return out[:max_chars] + ("..." if len(out) > max_chars else "")
    except Exception as e:
        return f"[Error loading PDF: {e}]"


def _ask_llm(prompt: str) -> str:
    """LLM call with Ollama client first, then HTTP fallback."""
    # Try Ollama Python client
    try:
        import ollama
        response = ollama.chat(
            model=CFG.llm_model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 256, "temperature": 0.2, "top_p": 0.9},
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
            return (data.get("response") or "").strip() or "[LLM returned empty response]"
        except Exception as api_error:
            return (
                f"[LLM unavailable - Ollama: {ollama_error}, API: {api_error}] "
                "Based on the context, I found relevant documents but cannot generate an answer."
            )
