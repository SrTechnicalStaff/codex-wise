"""Codex Wise provider package.

Sub-packages:
    llm/       — LLM providers (Codex app-server, Anthropic, OpenAI, OpenRouter, Gemini, Ollama, LiteLLM)
    embedding/ — Embedding providers (OpenAI, Gemini, Mock)

Preferred entry points:

    from codex_wise.core.providers.llm import get_provider
    from codex_wise.core.providers.embedding import get_embedder

    provider = get_provider("codex_app")
    response = await provider.generate(system_prompt="...", user_prompt="...")

    embedder = get_embedder("openai", api_key="sk-...")
    vectors = await embedder.embed(["text to embed"])

Backward-compatible imports still work:
    from codex_wise.core.providers import get_provider  # → llm.registry
"""

from codex_wise.core.providers.embedding import get_embedder, list_embedders, register_embedder
from codex_wise.core.providers.llm.base import (
    BaseProvider,
    ChatProvider,
    ChatStreamEvent,
    ChatToolCall,
    GeneratedResponse,
    ProviderError,
    RateLimitError,
)
from codex_wise.core.providers.llm.registry import get_provider, list_providers, register_provider

__all__ = [
    "BaseProvider",
    "ChatProvider",
    "ChatStreamEvent",
    "ChatToolCall",
    "GeneratedResponse",
    "ProviderError",
    "RateLimitError",
    "get_embedder",
    "get_provider",
    "list_embedders",
    "list_providers",
    "register_embedder",
    "register_provider",
]
