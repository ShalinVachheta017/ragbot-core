# rag_qdrant.py  (place in project root)
from dataclasses import dataclass
from typing import List, Any, Dict
from pathlib import Path

from core.qa import retrieve_candidates          # your real retriever
from core.config import CFG                      # your real config

# match UI's expected constant name
QDRANT_COLLECTION = CFG.qdrant_collection

@dataclass
class Hit:
    text: str
    source: str
    score: float
    payload: Dict[str, Any]

def search(query: str, top_k: int = 5) -> List[Hit]:
    """
    Adapter over core.qa.retrieve_candidates(query, CFG).
    Returns objects with .text/.source/.score like the UI uses.
    """
    raw = retrieve_candidates(query, CFG)  # returns List[core.qa.Hit]
    out: List[Hit] = []
    for h in raw[:top_k]:
        pl = h.payload or {}
        out.append(
            Hit(
                text=(h.text or pl.get("text", "")),
                source=str(pl.get("source_path", "")),
                score=float(h.score),
                payload=pl,
            )
        )
    return out

def abs_source_path(p: str | Path) -> str:
    """
    Make a source path absolute. If not found, fall back to data/extract/<filename>.
    """
    if not p:
        return ""
    p = Path(p)
    # already absolute and exists
    if p.exists():
        return str(p.resolve())
    # try under extract dir using just the filename
    candidate = Path(CFG.extract_dir) / p.name
    return str(candidate.resolve()) if candidate.exists() else str(p)
