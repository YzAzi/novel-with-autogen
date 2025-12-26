from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.agents.character_agent import CharacterAgent
from app.agents.outline_agent import OutlineAgent
from app.agents.writer_agent import WriterAgent
from app.db import crud
from app.db.models import Project


class Coordinator:
    name = "Coordinator"

    def __init__(self) -> None:
        self.outline_agent = OutlineAgent()
        self.character_agent = CharacterAgent()
        self.writer_agent = WriterAgent()

    def generate_outline(self, db: Session, project: Project, *, theme: str, total_words: int) -> Tuple[Project, List[Dict[str, Any]]]:
        coordinator_log = {
            "agent": self.name,
            "action": "dispatch",
            "summary": "调度生成大纲：OutlineAgent",
            "output_preview": None,
        }
        result = self.outline_agent.run(
            genre=project.genre,
            setting=project.setting,
            style=project.style,
            keywords=project.keywords,
            audience=project.audience,
            target_chapters=project.target_chapters,
            theme=theme,
            total_words=total_words,
        )
        logs = [coordinator_log, *result.logs]
        project = crud.update_project_artifacts(db, project, outline=result.data["outline"], append_logs=logs)
        return project, logs

    def generate_characters(self, db: Session, project: Project, *, constraints: str) -> Tuple[Project, List[Dict[str, Any]]]:
        coordinator_log = {
            "agent": self.name,
            "action": "dispatch",
            "summary": "调度生成角色：CharacterAgent",
            "output_preview": None,
        }
        result = self.character_agent.run(
            genre=project.genre,
            setting=project.setting,
            style=project.style,
            keywords=project.keywords,
            audience=project.audience,
            outline=project.outline,
            constraints=constraints,
        )
        logs = [coordinator_log, *result.logs]
        project = crud.update_project_artifacts(
            db,
            project,
            characters=result.data["characters"],
            characters_text=result.data.get("characters_text", ""),
            append_logs=logs,
        )
        return project, logs

    def expand_chapter(
        self,
        db: Session,
        project: Project,
        *,
        chapter_number: int,
        instruction: str,
        target_words: int,
    ) -> Tuple[Project, Dict[str, Any], List[Dict[str, Any]]]:
        coordinator_log = {
            "agent": self.name,
            "action": "dispatch",
            "summary": f"调度扩写章节：WriterAgent（第 {chapter_number} 章）",
            "output_preview": None,
        }
        result = self.writer_agent.run(
            chapter_number=chapter_number,
            context=instruction,
            target_words=target_words,
            style=project.style,
        )
        chapters = json.loads(project.chapters_json or "{}")
        chapters[str(chapter_number)] = result.data["text"]
        logs = [coordinator_log, *result.logs]
        project = crud.update_project_artifacts(db, project, chapters=chapters, append_logs=logs)
        return project, result.data, logs
