from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.core.config import settings


class LLMClient:
    def complete(self, *, system: str, prompt: str) -> str:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    def complete(self, *, system: str, prompt: str) -> str:
        # Deterministic-ish placeholder so the app works without any LLM.
        return (
            "【MOCK 模式输出】\n"
            f"System: {system.strip()[:120]}\n"
            f"Prompt: {prompt.strip()[:800]}\n"
            "\n（你可以在 .env 中设置 MOCK_LLM=0 并配置 LLM_* 环境变量启用真实 LLM）"
        )


class AutoGenLLMClient(LLMClient):
    def __init__(self) -> None:
        try:
            import autogen  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("autogen is not installed") from e

        self._autogen = autogen

        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is missing")

        config: Dict[str, Any] = {
            "model": settings.llm_model,
            "api_key": settings.llm_api_key,
        }
        if settings.llm_base_url:
            config["base_url"] = settings.llm_base_url

        self._llm_config = {
            "temperature": settings.llm_temperature,
            "config_list": [config],
        }

    def complete(self, *, system: str, prompt: str) -> str:
        # Minimal "single shot" usage: create a temporary assistant agent and ask it.
        agent = self._autogen.AssistantAgent(
            name="AutogenAssistant",
            system_message=system,
            llm_config=self._llm_config,
        )
        user = self._autogen.UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            code_execution_config=False,
        )
        # autogen stores last message in chat history; we return assistant's last content.
        user.initiate_chat(agent, message=prompt)
        history = user.chat_messages.get(agent, [])
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("content"):
                return str(msg["content"])
        return ""


def get_llm_client() -> LLMClient:
    if settings.mock_llm or not settings.llm_api_key:
        return MockLLMClient()
    return AutoGenLLMClient()

