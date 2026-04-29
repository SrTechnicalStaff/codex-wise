"""Provider configuration management — API keys, active provider, model selection.

Stores configuration in a server-side JSON file. Environment variables take
precedence over stored keys for each provider.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider catalog (hardcoded — add new providers here)
# ---------------------------------------------------------------------------

PROVIDER_CATALOG: list[dict[str, Any]] = [
    {
        "id": "codex",
        "name": "Codex",
        "default_model": "codex-default",
        "models": ["codex-default"],
        "env_keys": [],
        "requires_key": False,
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "default_model": "gemini-3.1-flash-lite-preview",
        "models": [
            "gemini-3.1-flash-lite-preview",
            "gemini-3-flash-preview",
            "gemini-3.1-pro-preview",
        ],
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "requires_key": True,
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "default_model": "claude-sonnet-4-6",
        "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "env_keys": ["ANTHROPIC_API_KEY"],
        "requires_key": True,
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "default_model": "gpt-5.4-nano",
        "models": ["gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4"],
        "env_keys": ["OPENAI_API_KEY"],
        "requires_key": True,
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "default_model": "anthropic/claude-sonnet-4.6",
        "models": [
            "anthropic/claude-sonnet-4.6",
            "google/gemini-3.1-flash-lite-preview",
            "meta-llama/llama-4-maverick",
            "openai/gpt-4o",
        ],
        "env_keys": ["OPENROUTER_API_KEY"],
        "requires_key": True,
    },
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "default_model": "llama3.2",
        "models": ["llama3.2", "codellama", "deepseek-coder-v2", "qwen2.5-coder"],
        "env_keys": [],
        "requires_key": False,
    },
    {
        "id": "litellm",
        "name": "LiteLLM",
        "default_model": "groq/llama-3.1-70b-versatile",
        "models": ["groq/llama-3.1-70b-versatile"],
        "env_keys": [],
        "requires_key": True,
    },
]

_CATALOG_BY_ID = {p["id"]: p for p in PROVIDER_CATALOG}


# ---------------------------------------------------------------------------
# Config file I/O
# ---------------------------------------------------------------------------


def _config_path() -> Path:
    config_dir = os.environ.get("CODEX_WISE_CONFIG_DIR", "")
    if config_dir:
        return Path(config_dir) / "provider_config.json"
    return Path("provider_config.json")


def _load_config() -> dict[str, Any]:
    path = _config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to read provider config, using defaults")
    return {}


def _save_config(config: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _get_key_for_provider(provider_id: str) -> str | None:
    """Get API key: env var takes precedence, then stored config."""
    catalog = _CATALOG_BY_ID.get(provider_id)
    if not catalog:
        return None

    # Check env vars first
    for env_key in catalog.get("env_keys", []):
        val = os.environ.get(env_key)
        if val:
            return val

    # Check stored config
    config = _load_config()
    keys = config.get("keys", {})
    return keys.get(provider_id)


def _get_base_url_for_provider(provider_id: str) -> str | None:
    """Resolve a provider base_url from environment variables."""
    env_map = {
        "anthropic": ["ANTHROPIC_BASE_URL"],
        "openai": ["OPENAI_BASE_URL"],
        "gemini": ["GEMINI_BASE_URL"],
        "ollama": ["OLLAMA_BASE_URL"],
        "litellm": ["LITELLM_BASE_URL", "LITELLM_API_BASE"],
    }
    for env_var in env_map.get(provider_id, []):
        val = os.environ.get(env_var)
        if val:
            return val
    return None


def _is_provider_configured(provider: dict[str, Any]) -> bool:
    if provider["id"] == "codex":
        try:
            from codex_wise.core.providers.llm.codex_app_server import is_codex_cli_available

            return is_codex_cli_available()
        except Exception:
            return False
    return bool(_get_key_for_provider(provider["id"])) or not provider["requires_key"]


def _build_provider_status(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    config = _load_config()
    active_id = config.get("active_provider")
    active_model = config.get("active_model")

    # Auto-detect active if not set
    if not active_id:
        for p in catalog:
            if _is_provider_configured(p):
                active_id = p["id"]
                active_model = p["default_model"]
                break

    providers = []
    catalog_by_id = {p["id"]: p for p in catalog}
    for p in catalog:
        providers.append(
            {
                "id": p["id"],
                "name": p["name"],
                "models": p["models"],
                "default_model": p["default_model"],
                "configured": _is_provider_configured(p),
                **({"model_details": p["model_details"]} if "model_details" in p else {}),
                **({"status_error": p["status_error"]} if "status_error" in p else {}),
            }
        )

    return {
        "active": {
            "provider": active_id,
            "model": active_model
            or (catalog_by_id.get(active_id, {}).get("default_model") if active_id else None),
        },
        "providers": providers,
    }


def list_provider_status() -> dict[str, Any]:
    """Return the full provider status including active selection."""
    return _build_provider_status(PROVIDER_CATALOG)


async def list_provider_status_async() -> dict[str, Any]:
    """Return provider status, hydrating Codex model metadata when available."""
    catalog = [dict(p) for p in PROVIDER_CATALOG]
    codex_provider = next((p for p in catalog if p["id"] == "codex"), None)
    if codex_provider is not None:
        try:
            from codex_wise.core.providers.llm.codex_app_server import (
                choose_codex_model,
                list_codex_models,
            )

            models = await list_codex_models(auto_login=False)
            if models:
                selection = choose_codex_model(models)
                codex_provider["models"] = [
                    str(m.get("model") or m.get("id"))
                    for m in models
                    if m.get("model") or m.get("id")
                ]
                codex_provider["default_model"] = selection.model
                codex_provider["model_details"] = models
        except Exception as exc:
            codex_provider["status_error"] = str(exc)
    return _build_provider_status(catalog)


def get_active_provider() -> tuple[str | None, str | None]:
    """Return (provider_id, model) for the currently active provider."""
    status = list_provider_status()
    active = status["active"]
    return active["provider"], active["model"]


def set_active_provider(provider_id: str, model: str | None = None) -> None:
    """Set the active provider and model. Persists to config file."""
    if provider_id not in _CATALOG_BY_ID:
        raise ValueError(f"Unknown provider: {provider_id}")
    config = _load_config()
    config["active_provider"] = provider_id
    if provider_id == "codex":
        config["active_model"] = model
    else:
        config["active_model"] = model or _CATALOG_BY_ID[provider_id]["default_model"]
    _save_config(config)


def set_api_key(provider_id: str, key: str | None) -> None:
    """Store or remove an API key for a provider."""
    if provider_id not in _CATALOG_BY_ID:
        raise ValueError(f"Unknown provider: {provider_id}")
    if provider_id == "codex":
        raise ValueError("Codex uses the Codex app-server account login; API keys are not supported.")
    config = _load_config()
    keys = config.setdefault("keys", {})
    if key:
        keys[provider_id] = key
    else:
        keys.pop(provider_id, None)
    _save_config(config)


def get_chat_provider_instance():
    """Create a provider instance for chat using the active config.

    Returns a provider that implements both BaseProvider and ChatProvider.
    """
    from codex_wise.core.providers.llm.registry import get_provider

    provider_id, model = get_active_provider()
    if not provider_id:
        raise ValueError("No active provider configured. Set an API key first.")

    api_key = _get_key_for_provider(provider_id)
    base_url = _get_base_url_for_provider(provider_id)
    catalog = _CATALOG_BY_ID[provider_id]

    kwargs: dict[str, Any] = {}
    if provider_id == "codex":
        if model and model != "codex-default":
            kwargs["model"] = model
    else:
        kwargs["model"] = model or catalog["default_model"]
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url

    return get_provider(provider_id, with_rate_limiter=False, **kwargs)
