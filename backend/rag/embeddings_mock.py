from __future__ import annotations

import hashlib
import random
from typing import List

from rag.embeddings_base import Embeddings


class MockEmbeddings(Embeddings):
    def __init__(self, *, dim: int = 256) -> None:
        self._dim = dim

    @property
    def model_name(self) -> str:
        return f"mock-hash-{self._dim}"

    def _vec_for(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(h[:16], 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(self._dim)]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._vec_for(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._vec_for(query)

