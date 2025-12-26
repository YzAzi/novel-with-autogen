from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Chunk:
    id: str
    project_id: str
    type: str
    text: str
    snippet: str
    score: float
    channel: str  # vector|keyword|rerank
    metadata: Dict[str, Any]
    created_at: dt.datetime | None = None


@dataclass
class RetrievalDebug:
    query: str
    vector_results: List[Chunk]
    keyword_results: List[Chunk]
    merged_candidates: List[Chunk]
    final_selected: List[Chunk]
    context_string: str

