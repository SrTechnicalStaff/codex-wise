"""Shared LLM provider resolution for server-side Codex Wise commands."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from repowise.core.providers.llm.base import BaseProvider
from repowise.core.providers.llm.registry import get_provider


@dataclass(frozen=True)
class ProviderResolution:
    provider: BaseProvider | None
    provider_name: str | None = None
    model_name: str | None = None
    explicit_provider: bool = False
    error: str | None = None


def get_env_alias(preferred: str, legacy: str, default: str | None = None) -> str | None:
    """Read the Codex Wise env var first, with Repowise as compatibility fallback."""
    return os.environ.get(preferred) or os.environ.get(legacy) or default


def resolve_llm_provider(
    provider_name: str | None = None,
    model: str | None = None,
    *,
    config: dict[str, Any] | None = None,
    allow_auto_detect: bool = True,
) -> ProviderResolution:
    """Resolve a provider for internal synthesis.

    Precedence:
      1. explicit argument / CODEX_WISE_PROVIDER
      2. legacy REPOWISE_PROVIDER
      3. optional config dict
      4. API-key / local-provider auto-detection

    Explicit provider failures are returned as errors and never fall through to
    other providers. That matters for CODEX_WISE_PROVIDER=codex_app: a broken
    app-server should produce an actionable retrieval-only result, not silently
    spend API-key quota through another provider.
    """

    cfg = config or {}
    configured_name = provider_name or get_env_alias("CODEX_WISE_PROVIDER", "REPOWISE_PROVIDER")
    configured_model = model or _resolve_model(cfg)
    explicit_provider = bool(configured_name)

    if not configured_name and isinstance(cfg.get("provider"), str):
        configured_name = cfg["provider"]
        explicit_provider = True

    if configured_name:
        return _try_provider(
            configured_name,
            configured_model,
            cfg,
            explicit_provider=explicit_provider,
        )

    if not allow_auto_detect:
        return ProviderResolution(provider=None, model_name=configured_model)

    last_error: str | None = None
    for name, env_key in (
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
    ):
        if _env_present(env_key):
            resolution = _try_provider(
                name,
                configured_model,
                cfg,
                explicit_provider=False,
            )
            if resolution.provider is not None:
                return resolution
            last_error = resolution.error

    if _env_present("GEMINI_API_KEY") or _env_present("GOOGLE_API_KEY"):
        resolution = _try_provider(
            "gemini",
            configured_model,
            cfg,
            explicit_provider=False,
        )
        if resolution.provider is not None:
            return resolution
        last_error = resolution.error

    if _env_present("OLLAMA_BASE_URL"):
        resolution = _try_provider(
            "ollama",
            configured_model,
            cfg,
            explicit_provider=False,
        )
        if resolution.provider is not None:
            return resolution
        last_error = resolution.error

    return ProviderResolution(provider=None, model_name=configured_model, error=last_error)


def _try_provider(
    name: str,
    model: str | None,
    cfg: dict[str, Any],
    *,
    explicit_provider: bool,
) -> ProviderResolution:
    kwargs = _provider_kwargs(name, model, cfg)
    try:
        provider = get_provider(name, **kwargs)
    except Exception as exc:
        return ProviderResolution(
            provider=None,
            provider_name=name,
            model_name=model,
            explicit_provider=explicit_provider,
            error=str(exc),
        )
    return ProviderResolution(
        provider=provider,
        provider_name=getattr(provider, "provider_name", name),
        model_name=getattr(provider, "model_name", model),
        explicit_provider=explicit_provider,
    )


def _provider_kwargs(name: str, model: str | None, cfg: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if model:
        kwargs["model"] = model

    base_url = _resolve_base_url(name, cfg)
    if base_url:
        kwargs["base_url"] = base_url

    if name == "anthropic" and _env_present("ANTHROPIC_API_KEY"):
        kwargs["api_key"] = os.environ["ANTHROPIC_API_KEY"]
    elif name == "openai" and _env_present("OPENAI_API_KEY"):
        kwargs["api_key"] = os.environ["OPENAI_API_KEY"]
    elif name == "openrouter" and _env_present("OPENROUTER_API_KEY"):
        kwargs["api_key"] = os.environ["OPENROUTER_API_KEY"]
    elif name == "gemini" and (_env_present("GEMINI_API_KEY") or _env_present("GOOGLE_API_KEY")):
        kwargs["api_key"] = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    elif name == "ollama" and _env_present("OLLAMA_BASE_URL"):
        kwargs["base_url"] = os.environ["OLLAMA_BASE_URL"]
    elif name == "codex_app":
        kwargs.update(_codex_app_kwargs())

    return kwargs


def _codex_app_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for env_var, key in (
        ("CODEX_WISE_CODEX_TRANSPORT", "transport"),
        ("CODEX_WISE_CODEX_APP_SERVER_URL", "app_server_url"),
        ("CODEX_WISE_CODEX_APP_SERVER_SOCKET", "socket_path"),
        ("CODEX_WISE_CODEX_TIMEOUT_SECONDS", "timeout_seconds"),
        ("CODEX_WISE_CODEX_REASONING_EFFORT", "reasoning_effort"),
        ("CODEX_WISE_CODEX_COMMAND", "command"),
    ):
        value = os.environ.get(env_var)
        if value:
            kwargs[key] = value
    return kwargs


def _resolve_model(cfg: dict[str, Any]) -> str | None:
    return (
        get_env_alias("CODEX_WISE_DOC_MODEL", "REPOWISE_DOC_MODEL")
        or get_env_alias("CODEX_WISE_MODEL", "REPOWISE_MODEL")
        or (cfg.get("model") if isinstance(cfg.get("model"), str) else None)
    )


def _resolve_base_url(name: str, cfg: dict[str, Any]) -> str | None:
    mapping = {
        "anthropic": ["ANTHROPIC_BASE_URL"],
        "openai": ["OPENAI_BASE_URL"],
        "openrouter": ["OPENROUTER_BASE_URL"],
        "gemini": ["GEMINI_BASE_URL"],
        "ollama": ["OLLAMA_BASE_URL"],
        "litellm": ["LITELLM_BASE_URL", "LITELLM_API_BASE"],
    }
    for env_var in mapping.get(name, []):
        value = os.environ.get(env_var)
        if value:
            return value
    section = cfg.get(name)
    if isinstance(section, dict) and section.get("base_url"):
        return str(section["base_url"])
    return None


def _env_present(name: str) -> bool:
    value = os.environ.get(name)
    return value is not None and value.strip() != ""


__all__ = ["ProviderResolution", "get_env_alias", "resolve_llm_provider"]
