from __future__ import annotations

from app.agents.llm import get_llm_client
from app.agents.types import AgentResult


class WriterAgent:
    name = "WriterAgent"

    def run(
        self,
        *,
        chapter_number: int,
        context: str,
        target_words: int,
        style: str,
    ) -> AgentResult:
        llm = get_llm_client()
        system = (
            "你是小说作者。你严格遵守大纲与角色设定，保持人物语言与动机一致，"
            "并且注意伏笔与前后呼应。输出正文，不要输出分析过程。"
        )
        prompt = f"""请扩写第 {chapter_number} 章，目标 {target_words} 字左右。

- 写作风格：{style}

请严格使用以下 Context（包含规则/大纲/角色/事实/伏笔/相关片段/用户指令）：
{context}

要求：
1) 章节包含标题（可选）+ 正文
2) 角色行为与动机必须与角色设定一致
3) 不要无缘由新增硬设定/关键道具
4) 与前文呼应、为后文埋伏笔
"""
        text = llm.complete(system=system, prompt=prompt)
        logs = [
            {
                "agent": self.name,
                "action": "expand_chapter",
                "summary": f"扩写第 {chapter_number} 章",
                "output_preview": text[:500],
            }
        ]
        return AgentResult(data={"chapter_number": chapter_number, "text": text}, logs=logs)
