from __future__ import annotations

from typing import Any

import pytest

from codex_wise.core.providers.llm.base import ProviderError
from codex_wise.core.providers.llm.codex_app import CodexAppProvider


class FakeClient:
    def __init__(self, messages: list[dict[str, Any]] | None = None) -> None:
        self.messages = list(messages or [])
        self.requests: list[tuple[str, dict[str, Any], float]] = []
        self.closed = False

    async def request(
        self, method: str, params: dict[str, Any] | None, timeout: float
    ) -> dict[str, Any]:
        self.requests.append((method, params or {}, timeout))
        if method == "thread/start":
            return {"thread": {"id": "thread-1"}}
        return {}

    async def receive(self, timeout: float) -> dict[str, Any]:
        if not self.messages:
            raise TimeoutError
        msg = self.messages.pop(0)
        if isinstance(msg, Exception):
            raise msg
        return msg

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_codex_app_provider_maps_prompts_model_and_usage() -> None:
    fake = FakeClient(
        [
            {
                "method": "thread/tokenUsage/updated",
                "params": {
                    "tokenUsage": {
                        "last": {
                            "inputTokens": 11,
                            "outputTokens": 7,
                            "cachedInputTokens": 3,
                            "totalTokens": 18,
                            "reasoningOutputTokens": 2,
                        }
                    }
                },
            },
            {"method": "item/agentMessage/delta", "params": {"delta": "hello "}},
            {"method": "item/agentMessage/delta", "params": {"delta": "world"}},
            {"method": "turn/completed", "params": {"turn": {"status": "completed"}}},
        ]
    )
    provider = CodexAppProvider(
        model="gpt-5.4-mini",
        timeout_seconds=12,
        client_factory=lambda: fake,
    )

    response = await provider.generate(
        "system rules",
        "user question",
        max_tokens=123,
        request_id="req-1",
    )

    assert provider.provider_name == "codex_app"
    assert provider.model_name == "gpt-5.4-mini"
    assert response.content == "hello world"
    assert response.input_tokens == 11
    assert response.output_tokens == 7
    assert response.cached_tokens == 3
    assert response.usage["reasoning_output_tokens"] == 2
    assert fake.closed is True

    methods = [method for method, _params, _timeout in fake.requests]
    assert methods == ["initialize", "thread/start", "turn/start"]
    thread_params = fake.requests[1][1]
    assert thread_params["developerInstructions"] == "system rules"
    assert thread_params["model"] == "gpt-5.4-mini"
    assert thread_params["approvalPolicy"] == "never"
    assert thread_params["sandbox"] == "read-only"

    turn_params = fake.requests[2][1]
    assert turn_params["threadId"] == "thread-1"
    assert turn_params["model"] == "gpt-5.4-mini"
    assert turn_params["effort"] == "medium"
    assert "user question" in turn_params["input"][0]["text"]
    assert "approximately 123 output tokens" in turn_params["input"][0]["text"]
    assert "Do not call tools" in turn_params["input"][0]["text"]


@pytest.mark.asyncio
async def test_codex_app_provider_defaults_to_gpt_55_medium() -> None:
    fake = FakeClient(
        [
            {
                "method": "item/completed",
                "params": {"item": {"type": "agentMessage", "text": "from item"}},
            },
            {"method": "turn/completed", "params": {"turn": {"status": "completed"}}},
        ]
    )
    provider = CodexAppProvider(client_factory=lambda: fake)

    response = await provider.generate("system", "user")

    assert provider.model_name == "gpt-5.5"
    assert response.content == "from item"
    assert fake.requests[1][1]["model"] == "gpt-5.5"
    assert fake.requests[2][1]["model"] == "gpt-5.5"
    assert fake.requests[2][1]["effort"] == "medium"
    assert response.usage == {"usage_unavailable": True}


@pytest.mark.asyncio
async def test_codex_app_provider_can_use_current_model_sentinel() -> None:
    fake = FakeClient(
        [
            {
                "method": "item/completed",
                "params": {"item": {"type": "agentMessage", "text": "from current"}},
            },
            {"method": "turn/completed", "params": {"turn": {"status": "completed"}}},
        ]
    )
    provider = CodexAppProvider(model="codex-current", client_factory=lambda: fake)

    response = await provider.generate("system", "user")

    assert provider.model_name == "codex-current"
    assert response.content == "from current"
    assert fake.requests[1][1].get("model") is None
    assert fake.requests[2][1].get("model") is None


@pytest.mark.asyncio
async def test_codex_app_provider_normalizes_turn_errors() -> None:
    fake = FakeClient(
        [
            {
                "method": "turn/completed",
                "params": {
                    "turn": {
                        "status": "failed",
                        "error": {"message": "model unavailable"},
                    }
                },
            }
        ]
    )
    provider = CodexAppProvider(client_factory=lambda: fake)

    with pytest.raises(ProviderError, match="model unavailable"):
        await provider.generate("system", "user")
    assert fake.closed is True


@pytest.mark.asyncio
async def test_codex_app_provider_normalizes_timeout() -> None:
    provider = CodexAppProvider(timeout_seconds=1, client_factory=lambda: FakeClient())

    with pytest.raises(ProviderError, match="timed out"):
        await provider.generate("system", "user")
