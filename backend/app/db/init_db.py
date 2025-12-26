from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    # SQLite FTS5 for keyword retrieval (hybrid RAG).
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS embeddings_cache (
              cache_key TEXT PRIMARY KEY,
              model_name TEXT NOT NULL,
              vector_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        try:
            conn.exec_driver_sql(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts
                USING fts5(
                  chunk_id UNINDEXED,
                  project_id UNINDEXED,
                  type UNINDEXED,
                  chapter_no UNINDEXED,
                  text
                );
                """
            )
        except Exception:
            # Allow running on SQLite builds without FTS5; keyword retrieval will fall back.
            pass
