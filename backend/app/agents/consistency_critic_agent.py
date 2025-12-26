from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from app.agents.llm import get_llm_client
from app.core.config import settings
from app.db.models import Project
from rag.types import Chunk


def _extract_names_from_project(project: Project) -> List[str]:
    try:
        obj = json.loads(project.characters_json or "{}")
        names = []
        for c in obj.get("characters", []):
            if isinstance(c, dict) and c.get("name"):
                names.append(str(c["name"]))
        return names
    except Exception:
        return []


class ConsistencyCriticAgent:
    name = "ConsistencyCriticAgent"

    def review(
        self,
        *,
        project: Project,
        chapter_no: int,
        draft_text: str,
        constraints: List[Chunk],
        context_used: str,
    ) -> Dict[str, Any]:
        if settings.critic_provider != "llm" or settings.mock_llm:
            return self._mock_review(project=project, chapter_no=chapter_no, draft_text=draft_text, context_used=context_used)

        llm = get_llm_client()
        system = (
            "你是一致性审稿（Consistency Critic）。"
            "你只输出严格 JSON，不要输出额外解释。"
            "默认只审查不重写；当 AUTO_REVISE=true 时可以给 revised_text。"
        )
        key_constraints = "\n\n".join([f"[{c.type}] {c.text}" for c in constraints[:10]])
        prompt = f"""请审查第 {chapter_no} 章草稿与以下关键约束的一致性，重点检查：
1) 人物动机/性格/关系是否自洽
2) 世界观硬设定是否被违反或无缘由新增
3) 时间线是否倒退或冲突
4) 伏笔是否与既有伏笔矛盾/是否错过回收条件

关键约束（RAG）：
{key_constraints}

草稿：
{draft_text}

输出严格 JSON：
{{
  "issues":[{{"issue_type":"character|world|timeline|foreshadowing|style","severity":"low|medium|high","conflict":"...","evidence_snippet":"..."}}],
  "suggested_edits":[{{"edit":"...","reason":"..."}}]
  {', "revised_text":"..."' if settings.auto_revise else ''}
}}
"""
        raw = llm.complete(system=system, prompt=prompt)
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            parsed = json.loads(raw[start : end + 1]) if start != -1 and end != -1 else {}
        except Exception:
            parsed = {}
        return {
            "issues": parsed.get("issues") if isinstance(parsed.get("issues"), list) else [],
            "suggested_edits": parsed.get("suggested_edits") if isinstance(parsed.get("suggested_edits"), list) else [],
            "revised_text": parsed.get("revised_text") if settings.auto_revise else None,
        }

    def _mock_review(self, *, project: Project, chapter_no: int, draft_text: str, context_used: str) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        names = _extract_names_from_project(project)
        if names:
            present = [n for n in names if n in draft_text]
            if not present:
                issues.append(
                    {
                        "issue_type": "character",
                        "severity": "medium",
                        "conflict": "本章正文未出现任何已知主角/主要角色名，可能导致人物一致性断裂或引入了未设定角色。",
                        "evidence_snippet": draft_text[:160],
                    }
                )

        # Very simple taboo check: if context contains a "禁忌" line, treat tokens after it as banned words.
        banned: List[str] = []
        for line in context_used.splitlines():
            if "禁忌" in line and ("：" in line or ":" in line):
                banned_part = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
                banned.extend([w.strip() for w in re.split(r"[,，、\s]+", banned_part) if w.strip()])
        banned = [b for b in banned if len(b) >= 2][:20]
        for w in banned:
            if w in draft_text:
                issues.append(
                    {
                        "issue_type": "style",
                        "severity": "low",
                        "conflict": f"命中禁忌词/提示词：{w}",
                        "evidence_snippet": w,
                    }
                )

        # Timeline hint
        if "回到" in draft_text and "昨天" in draft_text:
            issues.append(
                {
                    "issue_type": "timeline",
                    "severity": "low",
                    "conflict": "检测到可能的时间线倒退表述（“回到”“昨天”），请确认是否为回忆/倒叙并在文本中明确。",
                    "evidence_snippet": "回到…昨天…",
                }
            )

        return {"issues": issues, "suggested_edits": [], "revised_text": None}

