from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.agents.coordinator import Coordinator
from app.agents.consistency_critic_agent import ConsistencyCriticAgent
from app.db import crud
from app.db.models import Project
from app.schemas import CriticIssue, RetrievedChunkSummary
from app.services.writeback_extractor import WritebackExtractor
from rag.service import RAGService
from rag.types import Chunk


def _safe_json_loads(s: str, default):
    try:
        return json.loads(s or "")
    except Exception:
        return default


def _extract_character_names(characters_obj: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for c in (characters_obj or {}).get("characters", []) if isinstance(characters_obj, dict) else []:
        if isinstance(c, dict) and c.get("name"):
            names.append(str(c["name"]))
    return names


class ProjectService:
    def __init__(self) -> None:
        self.coordinator = Coordinator()
        self.rag = RAGService()
        self.extractor = WritebackExtractor()
        self.critic = ConsistencyCriticAgent()

    def get_or_404(self, db: Session, project_id: str) -> Project:
        project = crud.get_project(db, project_id)
        if not project:
            raise KeyError("project not found")
        return project

    def create_project(
        self,
        db: Session,
        *,
        genre: str,
        setting: str,
        style: str,
        keywords: str,
        audience: str,
        target_chapters: int,
    ) -> Tuple[Project, List[Dict[str, Any]]]:
        project = crud.create_project(
            db,
            genre=genre,
            setting=setting,
            style=style,
            keywords=keywords,
            audience=audience,
            target_chapters=target_chapters,
        )

        logs: List[Dict[str, Any]] = []
        for note in self.rag.pop_notes():
            logs.append({"agent": "RAG", "action": "fallback", "summary": note, "output_preview": None})

        # Seed style_guide + world as first-class memory.
        style_text = (
            "写作规则（style_guide）：\n"
            f"- 总体风格：{style}\n"
            "- 叙事要求：保持人物一致性、时间线单调推进、伏笔可回收。\n"
            "- 禁忌：不要突然新增硬设定；不要让角色无动机反转。\n"
        )
        style_doc = crud.upsert_source_document(
            db,
            project_id=project.id,
            type="style_guide",
            chapter_no=None,
            title="style_guide",
            text=style_text,
        )
        self.rag.index_document(
            project.id,
            "style_guide",
            style_text,
            {"source_id": style_doc.id, "project_id": project.id, "type": "style_guide"},
        )
        logs.append({"agent": "RAG", "action": "index", "summary": "已索引 style_guide", "output_preview": style_text[:240]})
        for note in self.rag.pop_notes():
            logs.append({"agent": "RAG", "action": "fallback", "summary": note, "output_preview": None})

        if setting.strip():
            world_doc = crud.upsert_source_document(
                db,
                project_id=project.id,
                type="world",
                chapter_no=None,
                title="world",
                text=setting,
            )
            self.rag.index_document(
                project.id,
                "world",
                setting,
                {"source_id": world_doc.id, "project_id": project.id, "type": "world"},
            )
            logs.append({"agent": "RAG", "action": "index", "summary": "已索引 world", "output_preview": setting[:240]})
            for note in self.rag.pop_notes():
                logs.append({"agent": "RAG", "action": "fallback", "summary": note, "output_preview": None})

        project = crud.update_project_artifacts(db, project, append_logs=logs)
        return project, logs

    def generate_outline(self, db: Session, project: Project, *, theme: str, total_words: int) -> Tuple[Project, List[Dict[str, Any]]]:
        project, logs = self.coordinator.generate_outline(db, project, theme=theme, total_words=total_words)
        doc = crud.upsert_source_document(
            db,
            project_id=project.id,
            type="outline",
            chapter_no=None,
            title="outline",
            text=project.outline,
        )
        self.rag.index_document(project.id, "outline", project.outline, {"source_id": doc.id, "project_id": project.id, "type": "outline"})
        rag_log = {"agent": "RAG", "action": "index", "summary": "已索引 outline", "output_preview": project.outline[:240]}
        fallback_logs = [{"agent": "RAG", "action": "fallback", "summary": note, "output_preview": None} for note in self.rag.pop_notes()]
        project = crud.update_project_artifacts(db, project, append_logs=[rag_log])
        if fallback_logs:
            project = crud.update_project_artifacts(db, project, append_logs=fallback_logs)
        return project, [*logs, rag_log, *fallback_logs]

    def generate_characters(
        self,
        db: Session,
        project: Project,
        *,
        constraints: str,
    ) -> Tuple[Project, List[Dict[str, Any]]]:
        project, logs = self.coordinator.generate_characters(db, project, constraints=constraints)
        characters_obj = _safe_json_loads(project.characters_json, {})
        names = _extract_character_names(characters_obj)
        combined_text = f"角色设定 JSON：\n{project.characters_json}\n\n角色总结：\n{project.characters_text}"
        doc = crud.upsert_source_document(
            db,
            project_id=project.id,
            type="characters",
            chapter_no=None,
            title="characters",
            text=combined_text,
        )
        self.rag.index_document(
            project.id,
            "characters",
            combined_text,
            {"source_id": doc.id, "project_id": project.id, "type": "characters", "characters": ",".join(names)},
        )
        rag_log = {"agent": "RAG", "action": "index", "summary": "已索引 characters", "output_preview": combined_text[:240]}
        fallback_logs = [{"agent": "RAG", "action": "fallback", "summary": note, "output_preview": None} for note in self.rag.pop_notes()]
        project = crud.update_project_artifacts(db, project, append_logs=[rag_log])
        if fallback_logs:
            project = crud.update_project_artifacts(db, project, append_logs=fallback_logs)
        return project, [*logs, rag_log, *fallback_logs]

    def expand_chapter(
        self,
        db: Session,
        project: Project,
        *,
        chapter_number: int,
        instruction: str,
        target_words: int,
    ) -> Tuple[Project, Dict[str, Any], List[Dict[str, Any]]]:
        # Retrieve first (hybrid RAG), then write.
        query = f"第{chapter_number}章 扩写：{instruction}".strip()
        characters_obj = _safe_json_loads(project.characters_json, {})
        names = _extract_character_names(characters_obj)
        retrieved = self.rag.retrieve(
            project.id,
            query,
            filters={
                "types": [
                    "style_guide",
                    "world",
                    "outline",
                    "characters",
                    "chapter_summary",
                    "facts",
                    "foreshadowing",
                    "chapter",
                ],
                "chapter_no": chapter_number,
                "chapter_only_before": True,
            },
            top_k=18,
        )
        fallback_logs = [{"agent": "RAG", "action": "fallback", "summary": note, "output_preview": None} for note in self.rag.pop_notes()]
        context = self.rag.build_context(
            {
                "outline": project.outline,
                "characters_json": project.characters_json,
                "setting": project.setting,
                "style": project.style,
            },
            retrieved,
        )
        context_with_instruction = (context + "\n\n## user instruction\n" + (instruction or "")).strip()

        project, writer_data, writer_logs = self.coordinator.expand_chapter(
            db,
            project,
            chapter_number=chapter_number,
            instruction=f"【请严格遵守以下检索到的上下文】\n\n{context_with_instruction}",
            target_words=target_words,
        )

        # Save chapter into normalized table for traceable source_id
        chapter = crud.upsert_chapter(db, project_id=project.id, chapter_no=chapter_number, text=writer_data["text"])
        # Index chapter text
        self.rag.index_document(
            project.id,
            "chapter",
            chapter.text,
            {
                "source_id": chapter.id,
                "project_id": project.id,
                "type": "chapter",
                "chapter_no": chapter_number,
                "characters": ",".join(names),
            },
        )

        rag_log = {"agent": "RAG", "action": "retrieve", "summary": f"扩写前检索到 {len(retrieved)} 条上下文", "output_preview": context[:400]}
        index_log = {"agent": "RAG", "action": "index", "summary": f"已索引 chapter #{chapter_number}", "output_preview": chapter.text[:240]}

        # Post-write extraction: summary / facts / foreshadowing
        extracted, extract_logs = self.extractor.extract(project=project, chapter_no=chapter_number, chapter_text=chapter.text)
        mem_logs: List[Dict[str, Any]] = []
        for mem_type, mem_text in extracted.items():
            mem = crud.add_chapter_memory(
                db,
                project_id=project.id,
                chapter_id=chapter.id,
                chapter_no=chapter_number,
                type=mem_type,
                text=mem_text,
            )
            self.rag.index_document(
                project.id,
                mem_type,
                mem_text,
                {
                    "source_id": mem.id,
                    "project_id": project.id,
                    "type": mem_type,
                    "chapter_no": chapter_number,
                    "characters": ",".join(names),
                },
            )
            mem_logs.append({"agent": "RAG", "action": "index", "summary": f"已索引 {mem_type}（第{chapter_number}章）", "output_preview": mem_text[:240]})

        # Critic: check consistency using key constraint types
        constraint_chunks = [c for c in retrieved if c.type in {"characters", "world", "facts", "outline"}]
        critic = self.critic.review(
            project=project,
            chapter_no=chapter_number,
            draft_text=chapter.text,
            constraints=constraint_chunks,
            context_used=context_with_instruction,
        )

        revised = False
        final_text = chapter.text
        if critic.get("revised_text"):
            revised = True
            final_text = str(critic["revised_text"])
            chapter = crud.upsert_chapter(db, project_id=project.id, chapter_no=chapter_number, text=final_text)
            self.rag.index_document(
                project.id,
                "chapter",
                final_text,
                {
                    "source_id": chapter.id,
                    "project_id": project.id,
                    "type": "chapter",
                    "chapter_no": chapter_number,
                    "characters": ",".join(names),
                },
            )
            chapters = _safe_json_loads(project.chapters_json, {})
            chapters[str(chapter_number)] = final_text
            project = crud.update_project_artifacts(db, project, chapters=chapters)

        critic_log = {
            "agent": "ConsistencyCriticAgent",
            "action": "review",
            "summary": f"一致性审查：issues={len(critic.get('issues') or [])} revised={revised}",
            "output_preview": json.dumps(critic.get("issues") or [], ensure_ascii=False)[:500],
        }

        project = crud.update_project_artifacts(
            db, project, append_logs=[*fallback_logs, rag_log, index_log, *extract_logs, *mem_logs, critic_log]
        )

        sources = [
            RetrievedChunkSummary(
                id=c.id,
                type=c.type,
                score=float(c.score),
                channel=c.channel,
                chapter_no=(c.metadata.get("chapter_no") if isinstance(c.metadata, dict) else None),
                source_id=(c.metadata.get("source_id") if isinstance(c.metadata, dict) else None),
                snippet=c.snippet,
            ).model_dump()
            for c in retrieved
        ]
        issues = [
            CriticIssue(**i).model_dump()
            for i in (critic.get("issues") or [])
            if isinstance(i, dict) and {"issue_type", "severity", "conflict"} <= set(i.keys())
        ]
        rag_info = {
            "context_used": (context_with_instruction[:4000] + ("…" if len(context_with_instruction) > 4000 else "")),
            "retrieved_context_sources": sources,
            "critic_issues": issues,
            "revised": revised,
        }

        data = {"chapter_number": chapter_number, "text": final_text, **rag_info}
        logs = [*writer_logs, *fallback_logs, rag_log, index_log, *extract_logs, *mem_logs, critic_log]
        return project, data, logs
