from __future__ import annotations

import asyncio
from typing import Any, Dict

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
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is missing")

        self._mode: str | None = None

        # AutoGen 0.4+ (agentchat + ext model clients)
        try:
            from autogen_agentchat.agents import AssistantAgent  # type: ignore

            self._AssistantAgent = AssistantAgent
            self._mode = "v0_4"
        except Exception:
            self._mode = None

        # Legacy AutoGen 0.2.x fallback (kept for compatibility if installed)
        if self._mode is None:
            try:
                import autogen  # type: ignore
            except Exception as e:  # pragma: no cover
                raise RuntimeError("AutoGen is not installed (need autogen-agentchat/autogen-ext[openai] 0.7.5)") from e

            self._autogen = autogen
            config: Dict[str, Any] = {"model": settings.llm_model, "api_key": settings.llm_api_key}
            if settings.llm_base_url:
                config["base_url"] = settings.llm_base_url
            self._llm_config = {"temperature": settings.llm_temperature, "config_list": [config]}
            self._mode = "legacy"

    def complete(self, *, system: str, prompt: str) -> str:
        if self._mode == "v0_4":
            try:
                from autogen_ext.models.openai import OpenAIChatCompletionClient  # type: ignore
                from autogen_ext.models.openai._model_info import ModelInfo  # type: ignore
            except Exception as e:  # pragma: no cover
                raise RuntimeError("AutoGen ext OpenAI client not available; install autogen-ext[openai]==0.7.5") from e

            model_kwargs: Dict[str, Any] = {
                "model": settings.llm_model,
                "api_key": settings.llm_api_key,
            }
            if settings.llm_base_url:
                model_kwargs["base_url"] = settings.llm_base_url

            # Many OpenAI-compatible gateways / non-OpenAI model IDs work better with explicit ModelInfo.
            model_kwargs["model_info"] = ModelInfo(
                model=settings.llm_model,
                family="openai-compatible",
                is_chat_model=True,
                vision=False,
                function_calling=False,
                json_output=False,
                structured_output=False,
            )

            model_client = OpenAIChatCompletionClient(**model_kwargs)
            agent = self._AssistantAgent(
                name="AutogenAssistant",
                system_message=system,
                model_client=model_client,
            )

            async def _run() -> str:
                result = await agent.run(task=prompt)
                messages = getattr(result, "messages", None)
                if messages:
                    last = messages[-1]
                    content = getattr(last, "content", None)
                    if content is not None:
                        return str(content)
                    return str(last)
                return str(result)

            return asyncio.run(_run())

        # legacy 0.2.x path
        agent = self._autogen.AssistantAgent(name="AutogenAssistant", system_message=system, llm_config=self._llm_config)
        user = self._autogen.UserProxyAgent(name="User", human_input_mode="NEVER", code_execution_config=False)
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
