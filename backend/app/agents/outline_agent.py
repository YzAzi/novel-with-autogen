from __future__ import annotations

from app.agents.llm import get_llm_client
from app.agents.types import AgentResult


class OutlineAgent:
    name = "OutlineAgent"

    def run(
        self,
        *,
        genre: str,
        setting: str,
        style: str,
        keywords: str,
        audience: str,
        target_chapters: int,
        theme: str,
        total_words: int,
    ) -> AgentResult:
        llm = get_llm_client()
        system = (
            "你是小说策划编辑。你擅长把用户需求拆成清晰的大纲（分卷/分章），"
            "并且章节之间有因果推进、伏笔与回收。输出可读的大纲文本。"
        )
        prompt = f"""请根据以下信息生成小说大纲（按“卷/章”结构，至少 {target_chapters} 章；每章 3-6 句梗概）：

- 题材：{genre}
- 世界观/设定：{setting}
- 风格：{style}
- 关键词：{keywords}
- 读者画像：{audience}
- 主题：{theme}
- 目标总字数：{total_words}
"""
        outline = llm.complete(system=system, prompt=prompt)
        logs = [
            {
                "agent": self.name,
                "action": "generate_outline",
                "summary": f"生成大纲（目标章节数={target_chapters}）",
                "output_preview": outline[:500],
            }
        ]
        return AgentResult(data={"outline": outline}, logs=logs)

