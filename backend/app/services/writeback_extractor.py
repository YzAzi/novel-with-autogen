from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from app.agents.llm import get_llm_client
from app.db.models import Project


class WritebackExtractor:
    name = "WritebackExtractor"

    def extract(self, *, project: Project, chapter_no: int, chapter_text: str) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
        """
        Returns dict: {chapter_summary, facts, foreshadowing} as strings (facts/foreshadowing are JSON strings).
        Must be runnable without a real LLM (get_llm_client() handles MOCK_LLM).
        """
        llm = get_llm_client()
        system = (
            "你是小说编辑助理。请在不改写正文的前提下，"
            "对章节进行：摘要（300-600字）、事实提炼、伏笔提炼。"
            "以严格 JSON 输出。"
        )
        prompt = f"""项目背景：
- 题材：{project.genre}
- 设定：{project.setting}
- 风格：{project.style}

请对第 {chapter_no} 章正文进行提炼：
正文：
{chapter_text}

输出严格 JSON：
{{
  "chapter_summary": "...(300-600字)",
  "facts": [
    {{"category":"character_state|relationship|location|world_rule|inventory|goal","subject":"...","change":"...","evidence":"..."}}
  ],
  "foreshadowing": [
    {{"hook":"...","clue":"...","expected_payoff":"...","range":"例如 第3-5章"}}
  ]
}}
"""
        raw = llm.complete(system=system, prompt=prompt)
        data: Dict[str, Any] = {}
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(raw[start : end + 1])
        except Exception:
            data = {}

        summary = str(data.get("chapter_summary") or raw[:600])
        facts = data.get("facts")
        foreshadowing = data.get("foreshadowing")
        facts_json = json.dumps(facts if isinstance(facts, list) else [], ensure_ascii=False, indent=2)
        foreshadowing_json = json.dumps(foreshadowing if isinstance(foreshadowing, list) else [], ensure_ascii=False, indent=2)

        logs = [
            {
                "agent": self.name,
                "action": "extract",
                "summary": f"写后提炼：summary/facts/foreshadowing（第{chapter_no}章）",
                "output_preview": summary[:280],
            }
        ]
        return {"chapter_summary": summary, "facts": facts_json, "foreshadowing": foreshadowing_json}, logs

