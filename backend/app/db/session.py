from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _sqlite_url(db_path: str) -> str:
    # Ensure directory exists (esp. for Docker volume mount).
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    return f"sqlite:///{db_path}"


engine = create_engine(
    _sqlite_url(settings.db_path),
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

