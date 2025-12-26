from __future__ import annotations

import json

from app.agents.llm import get_llm_client
from app.agents.types import AgentResult


class CharacterAgent:
    name = "CharacterAgent"

    def run(
        self,
        *,
        genre: str,
        setting: str,
        style: str,
        keywords: str,
        audience: str,
        outline: str,
        constraints: str,
    ) -> AgentResult:
        llm = get_llm_client()
        system = (
            "你是小说角色设定师与一致性审稿。请输出两部分："
            "1) 角色设定 JSON（严格 JSON）；2) 可读文本总结。"
        )
        prompt = f"""基于以下信息生成角色设定，并给出关系网与角色弧线。最后检查人物行为一致性（指出潜在矛盾点与修正建议）。

- 题材：{genre}
- 世界观/设定：{setting}
- 风格：{style}
- 关键词：{keywords}
- 读者画像：{audience}
- 大纲：{outline}
- 额外约束：{constraints}

请先输出严格 JSON，字段建议：
{{
  "characters": [{{"name": "...", "role": "...", "motivation": "...", "arc": "...", "traits": ["..."], "relationships": [{{"with": "...", "type": "...", "note": "..."}}]}}],
  "consistency_checks": [{{"risk": "...", "suggestion": "..."}}],
  "world_rules": ["..."]
}}
随后再输出一段可读总结。
"""
        raw = llm.complete(system=system, prompt=prompt)

        # Best-effort extract JSON block for storage; fallback to wrapper.
        characters_obj = {"raw": raw}
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                characters_obj = json.loads(raw[start : end + 1])
        except Exception:
            characters_obj = {"raw": raw}

        logs = [
            {
                "agent": self.name,
                "action": "generate_characters",
                "summary": "生成角色设定与一致性检查",
                "output_preview": raw[:500],
            }
        ]
        return AgentResult(data={"characters": characters_obj, "characters_text": raw}, logs=logs)

