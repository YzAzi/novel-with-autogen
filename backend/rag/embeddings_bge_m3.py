from __future__ import annotations

from typing import List

from rag.embeddings_base import Embeddings


class BgeM3Embeddings(Embeddings):
    def __init__(self, *, model_name: str = "BAAI/bge-m3", device: str | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("sentence-transformers is required for local_bge_m3") from e

        self._model_name = model_name
        self._model = SentenceTransformer(model_name, device=device)

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=16,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]

