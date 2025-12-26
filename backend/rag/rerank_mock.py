from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Sequence

from rag.rerank_base import Reranker


def _count_hits(query: str, text: str) -> int:
    hits = 0
    for token in re.split(r"[\s,，。；;、/]+", query.strip()):
        token = token.strip()
        if not token or len(token) < 2:
            continue
        hits += text.count(token)
    return hits


class MockReranker(Reranker):
    def __init__(self) -> None:
        pass

    @property
    def model_name(self) -> str:
        return "mock-weighted"

    def rerank(self, *, query: str, texts: Sequence[str]) -> List[float]:
        scores: List[float] = []
        for t in texts:
            hit = _count_hits(query, t)
            length_penalty = 1.0 / (1.0 + math.log(1 + max(len(t), 1)))
            scores.append(hit * 2.0 + length_penalty)
        return scores


def rule_score(
    *,
    query: str,
    text: str,
    meta: Dict[str, Any],
    base_score: float,
    target_chapter: int | None,
    type_weights: Dict[str, float],
) -> float:
    score = base_score
    score *= type_weights.get(str(meta.get("type", "")), 1.0)

    hits = _count_hits(query, text)
    score += min(3.0, hits * 0.5)

    if target_chapter and meta.get("chapter_no"):
        try:
            gap = max(0, int(target_chapter) - int(meta["chapter_no"]))
            score += 1.5 / (1.0 + gap)
        except Exception:
            pass

    if len(text) > 1600:
        score *= 0.85
    return score

