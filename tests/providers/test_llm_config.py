from __future__ import annotations

from typing import Any

import pytest

from repowise.core.providers.llm.base import BaseProvider, GeneratedResponse
from repowise.core.providers.llm.config import resolve_llm_provider


class FakeProvider(BaseProvider):
    def __init__(self, provider_name: str, model: str = "fake-model") -> None:
        self._provider_name = provider_name
        self._model = model

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        request_id: str | None = None,
    ) -> GeneratedResponse:
        return GeneratedResponse("ok", 0, 0)


def _clear_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "CODEX_WISE_PROVIDER",
        "CODEX_WISE_DOC_MODEL",
        "CODEX_WISE_MODEL",
        "CODEX_WISE_CODEX_TRANSPORT",
        "CODEX_WISE_CODEX_APP_SERVER_URL",
        "CODEX_WISE_CODEX_APP_SERVER_SOCKET",
        "CODEX_WISE_CODEX_TIMEOUT_SECONDS",
        "REPOWISE_PROVIDER",
        "REPOWISE_DOC_MODEL",
        "REPOWISE_MODEL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OLLAMA_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_codex_wise_provider_codex_app_selects_codex_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_get_provider(name: str, **kwargs: Any) -> FakeProvider:
        captured["name"] = name
        captured["kwargs"] = kwargs
        return FakeProvider(name, kwargs.get("model", "fake-model"))

    monkeypatch.setattr("repowise.core.providers.llm.config.get_provider", fake_get_provider)
    monkeypatch.setenv("CODEX_WISE_PROVIDER", "codex_app")
    monkeypatch.setenv("CODEX_WISE_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("CODEX_WISE_CODEX_TRANSPORT", "proxy")
    monkeypatch.setenv("CODEX_WISE_CODEX_TIMEOUT_SECONDS", "42")

    resolution = resolve_llm_provider()

    assert resolution.provider is not None
    assert resolution.provider_name == "codex_app"
    assert resolution.model_name == "gpt-5.4-mini"
    assert resolution.explicit_provider is True
    assert captured["name"] == "codex_app"
    assert captured["kwargs"]["model"] == "gpt-5.4-mini"
    assert captured["kwargs"]["transport"] == "proxy"
    assert captured["kwargs"]["timeout_seconds"] == "42"


def test_legacy_repowise_provider_still_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_provider_env(monkeypatch)

    def fake_get_provider(name: str, **kwargs: Any) -> FakeProvider:
        return FakeProvider(name, kwargs.get("model", "fake-model"))

    monkeypatch.setattr("repowise.core.providers.llm.config.get_provider", fake_get_provider)
    monkeypatch.setenv("REPOWISE_PROVIDER", "openai")
    monkeypatch.setenv("REPOWISE_MODEL", "legacy-model")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    resolution = resolve_llm_provider()

    assert resolution.provider is not None
    assert resolution.provider_name == "openai"
    assert resolution.model_name == "legacy-model"


def test_explicit_api_key_provider_still_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_provider_env(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_get_provider(name: str, **kwargs: Any) -> FakeProvider:
        captured["name"] = name
        captured["kwargs"] = kwargs
        return FakeProvider(name, kwargs.get("model", "fake-model"))

    monkeypatch.setattr("repowise.core.providers.llm.config.get_provider", fake_get_provider)
    monkeypatch.setenv("CODEX_WISE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    resolution = resolve_llm_provider(model="gpt-5.4-mini")

    assert resolution.provider is not None
    assert resolution.provider_name == "openai"
    assert captured["kwargs"]["api_key"] == "sk-test"
    assert captured["kwargs"]["model"] == "gpt-5.4-mini"


def test_auto_detect_api_key_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_provider_env(monkeypatch)

    def fake_get_provider(name: str, **kwargs: Any) -> FakeProvider:
        return FakeProvider(name, kwargs.get("model", "fake-model"))

    monkeypatch.setattr("repowise.core.providers.llm.config.get_provider", fake_get_provider)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    resolution = resolve_llm_provider()

    assert resolution.provider is not None
    assert resolution.provider_name == "anthropic"
    assert resolution.explicit_provider is False


def test_explicit_codex_app_failure_does_not_fall_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)

    def fake_get_provider(name: str, **kwargs: Any) -> FakeProvider:
        if name == "codex_app":
            raise RuntimeError("app-server unavailable")
        raise AssertionError(f"unexpected fallback to {name}")

    monkeypatch.setattr("repowise.core.providers.llm.config.get_provider", fake_get_provider)
    monkeypatch.setenv("CODEX_WISE_PROVIDER", "codex_app")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    resolution = resolve_llm_provider()

    assert resolution.provider is None
    assert resolution.provider_name == "codex_app"
    assert resolution.explicit_provider is True
    assert "app-server unavailable" in (resolution.error or "")
