from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence, Tuple


class Reranker(ABC):
    @abstractmethod
    def rerank(self, *, query: str, texts: Sequence[str]) -> List[float]:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

