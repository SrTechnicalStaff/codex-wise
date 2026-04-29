"""Unit tests for GeminiEmbedder.

The google-genai SDK is faked here; no network calls are made.
"""

from __future__ import annotations

import math
import sys
import types
from types import SimpleNamespace

from codex_wise.core.providers.embedding.gemini import GeminiEmbedder


def _install_fake_google_genai(monkeypatch, calls: list[dict]) -> None:
    google_mod = types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")
    genai_types_mod = types.ModuleType("google.genai.types")

    class FakeModels:
        def embed_content(self, *, model, contents, config):
            calls.append({"model": model, "contents": contents, "config": config})
            return SimpleNamespace(
                embeddings=[SimpleNamespace(values=[1.0, 0.0, 0.0])]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    def fake_embed_content_config(**kwargs):
        return kwargs

    genai_mod.Client = FakeClient
    genai_mod.types = genai_types_mod
    genai_types_mod.EmbedContentConfig = fake_embed_content_config
    genai_types_mod.HttpOptions = lambda **kwargs: kwargs
    google_mod.genai = genai_mod

    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai_types_mod)


def test_default_model_is_gemini_embedding_2(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.delenv("CODEX_WISE_EMBEDDING_MODEL", raising=False)

    embedder = GeminiEmbedder()

    assert embedder._model == "gemini-embedding-2"
    assert embedder.dimensions == 768


def test_env_model_override(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("CODEX_WISE_EMBEDDING_MODEL", "gemini-embedding-001")

    embedder = GeminiEmbedder()

    assert embedder._model == "gemini-embedding-001"


def test_provider_specific_env_model_override_wins(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("CODEX_WISE_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("CODEX_WISE_GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

    embedder = GeminiEmbedder()

    assert embedder._model == "gemini-embedding-2"


def test_embedding_2_query_and_document_format(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    embedder = GeminiEmbedder(query_task="question answering")

    assert embedder.prepare_query("How does auth work?") == (
        "task: question answering | query: How does auth work?"
    )
    assert embedder.prepare_document("Details", "Auth Service") == (
        "title: Auth Service | text: Details"
    )
    assert embedder.prepare_document("Details") == "title: none | text: Details"


async def test_embedding_2_embeds_each_text_separately_without_task_type(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    calls: list[dict] = []
    _install_fake_google_genai(monkeypatch, calls)
    embedder = GeminiEmbedder(model="gemini-embedding-2", output_dimensionality=768)

    result = await embedder.embed(["first", "second"])

    assert len(result) == 2
    assert len(calls) == 2
    assert calls[0]["contents"] == "first"
    assert calls[1]["contents"] == "second"
    assert calls[0]["config"] == {"output_dimensionality": 768}
    assert math.isclose(math.sqrt(sum(x * x for x in result[0])), 1.0)


async def test_embedding_1_keeps_batch_and_task_type(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    calls: list[dict] = []
    _install_fake_google_genai(monkeypatch, calls)
    embedder = GeminiEmbedder(model="gemini-embedding-001", output_dimensionality=768)

    await embedder.embed(["first", "second"])

    assert len(calls) == 1
    assert calls[0]["contents"] == ["first", "second"]
    assert calls[0]["config"] == {
        "output_dimensionality": 768,
        "task_type": "SEMANTIC_SIMILARITY",
    }
