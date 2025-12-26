from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    db_path: str = "/data/app.db"
    backend_cors_origins: str = "http://localhost:3000"

    mock_llm: bool = True
    llm_provider: str = "openai_compatible"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7

    # RAG
    chroma_persist_dir: str = "data/chroma"
    embeddings_provider: str = "mock"  # local_bge_m3|mock
    bge_m3_model_name: str = "BAAI/bge-m3"
    rerank_provider: str = "mock"  # local_bge|mock
    bge_rerank_model_name: str = "BAAI/bge-reranker-v2-m3"
    rag_device: str | None = None  # e.g. "cpu" or "cuda"
    rag_max_chunk_chars: int = 1400
    rag_overlap_ratio: float = 0.2
    rag_top_k_v: int = 10
    rag_top_k_kw: int = 10

    # Critic
    critic_provider: str = "mock"  # llm|mock
    auto_revise: bool = False

    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


settings = Settings()
