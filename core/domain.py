# core/domain.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional

@dataclass
class DocumentPage:
    page_number: int
    text: str
    source_path: Path
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_langchain_like(self) -> Dict[str, Any]:
        return {
            "page_content": self.text,
            "metadata": {
                "source": str(self.source_path),
                "page": self.page_number,
                **self.meta,
            },
        }

@dataclass
class DocumentChunk:
    chunk_index: int
    text: str
    source_path: Path
    page_start: int
    page_end: int
    meta: Dict[str, Any] = field(default_factory=dict)

    def payload(self) -> Dict[str, Any]:
        return {
            "source_path": str(self.source_path),
            "chunk_idx": self.chunk_index,
            "page_start": self.page_start,
            "page_end": self.page_end,
            **self.meta,
        }
