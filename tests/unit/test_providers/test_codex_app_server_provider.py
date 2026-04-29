"""Unit tests for the Codex app-server provider."""

from __future__ import annotations

import pytest

from codex_wise.core.providers.llm.base import GeneratedResponse, ProviderError
from codex_wise.core.providers.llm.codex_app_server import (
    CodexAppServerProvider,
    choose_codex_model,
)


def _models() -> list[dict]:
    return [
        {
            "id": "gpt-5.5",
            "model": "gpt-5.5",
            "displayName": "GPT-5.5",
            "hidden": False,
            "isDefault": True,
            "defaultReasoningEffort": "medium",
            "supportedReasoningEfforts": [
                {"reasoningEffort": "low"},
                {"reasoningEffort": "medium"},
                {"reasoningEffort": "high"},
            ],
        },
        {
            "id": "gpt-5.4-mini",
            "model": "gpt-5.4-mini",
            "displayName": "GPT-5.4 Mini",
            "hidden": False,
            "isDefault": False,
            "defaultReasoningEffort": "low",
            "supportedReasoningEfforts": [{"reasoningEffort": "low"}],
        },
    ]


class FakeCodexClient:
    def __init__(self) -> None:
        self.connected = False
        self.auth_kwargs: dict | None = None
        self.generate_kwargs: dict | None = None

    async def connect(self) -> None:
        self.connected = True

    async def ensure_authenticated(self, **kwargs):
        self.auth_kwargs = kwargs
        return {"account": {"type": "chatgpt"}}

    async def list_models(self, *, include_hidden: bool = False):
        return _models()

    async def generate_turn(self, **kwargs):
        self.generate_kwargs = kwargs
        return GeneratedResponse(
            content="# Generated",
            input_tokens=123,
            output_tokens=45,
            cached_tokens=6,
            usage={"input_tokens": 123, "output_tokens": 45},
        )

    async def read_rate_limits(self):
        return {"rateLimits": {"limitId": "codex"}}

    async def close(self) -> None:
        self.connected = False


def test_choose_codex_model_uses_live_default():
    selection = choose_codex_model(_models())

    assert selection.model == "gpt-5.5"
    assert selection.reasoning_effort == "medium"


def test_choose_codex_model_respects_requested_model_and_effort():
    selection = choose_codex_model(
        _models(),
        requested_model="gpt-5.4-mini",
        requested_effort="low",
    )

    assert selection.model == "gpt-5.4-mini"
    assert selection.reasoning_effort == "low"


def test_choose_codex_model_rejects_unsupported_effort():
    with pytest.raises(ProviderError):
        choose_codex_model(
            _models(),
            requested_model="gpt-5.4-mini",
            requested_effort="high",
        )


async def test_generate_uses_codex_auth_model_and_turn_defaults(tmp_path):
    fake_client = FakeCodexClient()
    provider = CodexAppServerProvider(
        cwd=tmp_path,
        client_factory=lambda: fake_client,
    )

    result = await provider.generate("system", "user", max_tokens=1000)

    assert result.content == "# Generated"
    assert result.input_tokens == 123
    assert result.output_tokens == 45
    assert result.cached_tokens == 6
    assert result.usage["rate_limits"]["rateLimits"]["limitId"] == "codex"
    assert provider.model_name == "gpt-5.5"
    assert fake_client.connected is True
    assert fake_client.auth_kwargs == {
        "auto_login": True,
        "login_timeout": 300.0,
    }
    assert fake_client.generate_kwargs["model"] == "gpt-5.5"
    assert fake_client.generate_kwargs["reasoning_effort"] == "medium"
    assert fake_client.generate_kwargs["cwd"] == str(tmp_path.resolve())


async def test_generate_respects_requested_model_and_reasoning_effort():
    fake_client = FakeCodexClient()
    provider = CodexAppServerProvider(
        model="gpt-5.4-mini",
        reasoning_effort="low",
        client_factory=lambda: fake_client,
    )

    await provider.generate("system", "user")

    assert provider.model_name == "gpt-5.4-mini"
    assert fake_client.generate_kwargs["model"] == "gpt-5.4-mini"
    assert fake_client.generate_kwargs["reasoning_effort"] == "low"
