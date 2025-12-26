from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Chapter, ChapterMemory, Project, SourceDocument


def create_project(
    db: Session,
    *,
    genre: str,
    setting: str,
    style: str,
    keywords: str,
    audience: str,
    target_chapters: int,
) -> Project:
    project = Project(
        genre=genre,
        setting=setting,
        style=style,
        keywords=keywords,
        audience=audience,
        target_chapters=target_chapters,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: str) -> Optional[Project]:
    return db.get(Project, project_id)


def update_project_artifacts(
    db: Session,
    project: Project,
    *,
    outline: str | None = None,
    characters: Dict[str, Any] | None = None,
    characters_text: str | None = None,
    chapters: Dict[str, str] | None = None,
    append_logs: List[Dict[str, Any]] | None = None,
) -> Project:
    if outline is not None:
        project.outline = outline
    if characters is not None:
        project.characters_json = json.dumps(characters, ensure_ascii=False, indent=2)
    if characters_text is not None:
        project.characters_text = characters_text
    if chapters is not None:
        project.chapters_json = json.dumps(chapters, ensure_ascii=False, indent=2)
    if append_logs:
        existing = json.loads(project.agent_logs_json or "[]")
        existing.extend(append_logs)
        project.agent_logs_json = json.dumps(existing, ensure_ascii=False, indent=2)

    project.updated_at = dt.datetime.now(dt.timezone.utc)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def upsert_source_document(
    db: Session,
    *,
    project_id: str,
    type: str,
    chapter_no: int | None,
    title: str,
    text: str,
) -> SourceDocument:
    # Simple strategy: always create a new version.
    doc = SourceDocument(project_id=project_id, type=type, chapter_no=chapter_no, title=title, text=text)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def upsert_chapter(db: Session, *, project_id: str, chapter_no: int, text: str) -> Chapter:
    chapter = (
        db.query(Chapter)
        .filter(Chapter.project_id == project_id)
        .filter(Chapter.chapter_no == chapter_no)
        .one_or_none()
    )
    if chapter is None:
        chapter = Chapter(project_id=project_id, chapter_no=chapter_no, text=text)
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        return chapter
    chapter.text = text
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def add_chapter_memory(
    db: Session,
    *,
    project_id: str,
    chapter_id: str,
    chapter_no: int,
    type: str,
    text: str,
) -> ChapterMemory:
    mem = ChapterMemory(project_id=project_id, chapter_id=chapter_id, chapter_no=chapter_no, type=type, text=text)
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem
