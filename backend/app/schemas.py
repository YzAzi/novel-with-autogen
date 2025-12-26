from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, PositiveInt


class AgentLog(BaseModel):
    ts: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    agent: str
    action: str
    summary: str
    output_preview: str | None = None


class APIError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class APIResponse(BaseModel):
    data: Any | None = None
    error: APIError | None = None
    agent_logs: List[AgentLog] = []


class ProjectCreateRequest(BaseModel):
    genre: str = Field(min_length=1, max_length=200)
    setting: str = Field(default="", max_length=4000)
    style: str = Field(default="", max_length=200)
    keywords: str = Field(default="", max_length=1000)
    audience: str = Field(default="", max_length=1000)
    target_chapters: PositiveInt = Field(default=10, le=200)


class ProjectState(BaseModel):
    id: str
    genre: str
    setting: str
    style: str
    keywords: str
    audience: str
    target_chapters: int
    outline: str
    characters: Dict[str, Any]
    characters_text: str
    chapters: Dict[str, str]
    created_at: dt.datetime
    updated_at: dt.datetime


class OutlineRequest(BaseModel):
    theme: str = Field(default="", max_length=500)
    total_words: int = Field(default=80000, ge=1000, le=2_000_000)


class CharactersRequest(BaseModel):
    constraints: str = Field(default="", max_length=2000)


class ExpandChapterRequest(BaseModel):
    instruction: str = Field(default="", max_length=2000)
    target_words: int = Field(default=2500, ge=200, le=20000)


class ExpandChapterResponse(BaseModel):
    chapter_number: int
    text: str


class RetrievedChunkSummary(BaseModel):
    id: str
    type: str
    score: float
    channel: str
    chapter_no: int | None = None
    source_id: str | None = None
    snippet: str


class CriticIssue(BaseModel):
    issue_type: str
    severity: str
    conflict: str
    evidence_snippet: str | None = None


class ExpandChapterRagInfo(BaseModel):
    context_used: str
    retrieved_context_sources: List[RetrievedChunkSummary]
    critic_issues: List[CriticIssue]
    revised: bool = False


class RagStatsItem(BaseModel):
    chunks: int
    last_updated_at: Any | None = None


class RagPreviewResponse(BaseModel):
    query: str
    vector_results: List[RetrievedChunkSummary]
    keyword_results: List[RetrievedChunkSummary]
    merged_candidates: List[RetrievedChunkSummary]
    final_selected: List[RetrievedChunkSummary]
    final_selected_grouped: Dict[str, List[RetrievedChunkSummary]] = {}
    context_string: str
