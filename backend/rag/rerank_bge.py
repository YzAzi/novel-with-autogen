from __future__ import annotations

from typing import List, Sequence

from rag.rerank_base import Reranker


class BgeReranker(Reranker):
    def __init__(self, *, model_name: str = "BAAI/bge-reranker-v2-m3", device: str | None = None) -> None:
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("sentence-transformers is required for local_bge reranker") from e

        self._model_name = model_name
        self._model = CrossEncoder(model_name, device=device)

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank(self, *, query: str, texts: Sequence[str]) -> List[float]:
        pairs = [[query, t] for t in texts]
        scores = self._model.predict(pairs, batch_size=16, show_progress_bar=False)
        return [float(s) for s in scores]

