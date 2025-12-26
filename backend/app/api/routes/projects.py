from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.agents.coordinator import Coordinator
from app.db import crud
from app.db.session import get_db
from app.schemas import (
    APIResponse,
    RagPreviewResponse,
    RagStatsItem,
    CharactersRequest,
    CriticIssue,
    ExpandChapterRequest,
    ExpandChapterResponse,
    ExpandChapterRagInfo,
    OutlineRequest,
    ProjectCreateRequest,
    ProjectState,
    RetrievedChunkSummary,
)
from app.services.project_service import ProjectService
from rag.service import RAGService


router = APIRouter()
projects = ProjectService()
rag = RAGService()


def _project_state(project) -> ProjectState:
    return ProjectState(
        id=project.id,
        genre=project.genre,
        setting=project.setting,
        style=project.style,
        keywords=project.keywords,
        audience=project.audience,
        target_chapters=project.target_chapters,
        outline=project.outline or "",
        characters=json.loads(project.characters_json or "{}"),
        characters_text=project.characters_text or "",
        chapters=json.loads(project.chapters_json or "{}"),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _logs_tail(project, limit: int = 50) -> List[Dict[str, Any]]:
    logs = json.loads(project.agent_logs_json or "[]")
    return logs[-limit:]

def _project_or_404(db: Session, project_id: str):
    try:
        return projects.get_or_404(db, project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="project not found")


@router.post("/projects", response_model=APIResponse)
def create_project(payload: ProjectCreateRequest, db: Session = Depends(get_db)):
    project, logs = projects.create_project(
        db,
        genre=payload.genre,
        setting=payload.setting,
        style=payload.style,
        keywords=payload.keywords,
        audience=payload.audience,
        target_chapters=int(payload.target_chapters),
    )
    return APIResponse(data=_project_state(project), error=None, agent_logs=logs)


@router.get("/projects/{project_id}", response_model=APIResponse)
def get_project(project_id: str = Path(min_length=1), db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return APIResponse(data=_project_state(project), error=None, agent_logs=_logs_tail(project))


@router.post("/projects/{project_id}/outline", response_model=APIResponse)
def generate_outline(project_id: str, payload: OutlineRequest, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    project, logs = projects.generate_outline(db, project, theme=payload.theme, total_words=payload.total_words)
    return APIResponse(data=_project_state(project), error=None, agent_logs=logs)


@router.post("/projects/{project_id}/characters", response_model=APIResponse)
def generate_characters(project_id: str, payload: CharactersRequest, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    if not (project.outline or "").strip():
        raise HTTPException(status_code=400, detail="outline is empty; generate outline first")
    project, logs = projects.generate_characters(db, project, constraints=payload.constraints)
    return APIResponse(data=_project_state(project), error=None, agent_logs=logs)


@router.post("/projects/{project_id}/chapters/{chapter_number}/expand", response_model=APIResponse)
def expand_chapter(
    project_id: str,
    chapter_number: int = Path(ge=1, le=200),
    payload: ExpandChapterRequest = ...,
    db: Session = Depends(get_db),
):
    project = _project_or_404(db, project_id)
    if not (project.outline or "").strip():
        raise HTTPException(status_code=400, detail="outline is empty; generate outline first")
    if not (project.characters_json or "").strip() or project.characters_json.strip() == "{}":
        raise HTTPException(status_code=400, detail="characters are empty; generate characters first")
    project, data, logs = projects.expand_chapter(
        db,
        project,
        chapter_number=chapter_number,
        instruction=payload.instruction,
        target_words=payload.target_words,
    )
    return APIResponse(data=data, error=None, agent_logs=logs)


@router.get("/projects/{project_id}/rag/stats", response_model=APIResponse)
def rag_stats(project_id: str, db: Session = Depends(get_db)):
    _ = _project_or_404(db, project_id)
    stats = rag.stats(project_id)
    return APIResponse(data=stats, error=None, agent_logs=[])


@router.get("/projects/{project_id}/rag/preview", response_model=APIResponse)
def rag_preview(
    project_id: str,
    chapter: int | None = None,
    query: str | None = None,
    top_k: int = 18,
    db: Session = Depends(get_db),
):
    _ = _project_or_404(db, project_id)
    q = (query or "").strip() or (f"第{chapter}章" if chapter else "写作一致性检索")
    debug = rag.preview(project_id=project_id, query=q, chapter_no=chapter, top_k=top_k)

    def summarize(chunks):
        out = []
        for c in chunks:
            out.append(
                {
                    "id": c.id,
                    "type": c.type,
                    "score": float(c.score),
                    "channel": c.channel,
                    "chapter_no": c.metadata.get("chapter_no") if isinstance(c.metadata, dict) else None,
                    "source_id": c.metadata.get("source_id") if isinstance(c.metadata, dict) else None,
                    "snippet": c.snippet,
                }
            )
        return out

    payload = RagPreviewResponse(
        query=q,
        vector_results=summarize(debug.vector_results),
        keyword_results=summarize(debug.keyword_results),
        merged_candidates=summarize(debug.merged_candidates),
        final_selected=summarize(debug.final_selected),
        final_selected_grouped={
            t: summarize([c for c in debug.final_selected if c.type == t])
            for t in sorted({c.type for c in debug.final_selected})
        },
        context_string=(debug.context_string + "\n\n## user instruction\n" + q).strip(),
    ).model_dump()
    return APIResponse(data=payload, error=None, agent_logs=[])
