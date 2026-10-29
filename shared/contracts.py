"""Shared handoff types. Keep IDs stable across baseline/custom embeddings."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source: str
    page: Optional[int] = None  # one-based PDF page; None for non-PDF text

@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float  # higher means more similar; not comparable across backends
