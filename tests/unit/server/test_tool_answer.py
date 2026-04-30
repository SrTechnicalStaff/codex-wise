from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from codex_wise.core.persistence.database import init_db
from codex_wise.core.persistence.models import AnswerCache, Page, Repository
from codex_wise.core.persistence.search import SearchResult
from codex_wise.core.providers.llm.base import BaseProvider, GeneratedResponse
from codex_wise.core.providers.llm.config import ProviderResolution

_NOW = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)


class FakeFts:
    def __init__(self, page_id: str = "file_page:src/auth/service.py") -> None:
        self.page_id = page_id

    async def search(self, question: str, limit: int = 15) -> list[SearchResult]:
        return [
            SearchResult(
                page_id=self.page_id,
                title="Auth Service",
                page_type="file_page",
                target_path="src/auth/service.py",
                score=4.0,
                snippet="authentication service",
                search_type="fulltext",
            )
        ]


class FakeProvider(BaseProvider):
    def __init__(
        self,
        content: str = "Auth is handled in src/auth/service.py.",
        *,
        provider_name: str = "codex_app",
        model_name: str = "gpt-5.4-mini",
        exc: Exception | None = None,
    ) -> None:
        self._content = content
        self._provider_name = provider_name
        self._model_name = model_name
        self._exc = exc
        self.calls: list[dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        request_id: str | None = None,
    ) -> GeneratedResponse:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if self._exc is not None:
            raise self._exc
        return GeneratedResponse(self._content, 10, 6)


@pytest.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_db(eng)
    yield eng
    await eng.dispose()


@pytest.fixture
async def factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def repo_with_page(factory, tmp_path: Path) -> str:
    async with factory() as session:
        repo = Repository(
            id="repo1",
            name="test-repo",
            url="",
            local_path=str(tmp_path),
            default_branch="main",
            settings_json="{}",
            created_at=_NOW,
            updated_at=_NOW,
        )
        page = Page(
            id="file_page:src/auth/service.py",
            repository_id="repo1",
            page_type="file_page",
            title="Auth Service",
            content="# Auth Service\n\nHandles login and token checks.",
            summary="Handles login and token checks.",
            target_path="src/auth/service.py",
            source_hash="sha",
            model_name="mock",
            provider_name="mock",
            generation_level=2,
            confidence=0.9,
            freshness_status="fresh",
            metadata_json="{}",
            created_at=_NOW,
            updated_at=_NOW,
        )
        session.add_all([repo, page])
        await session.commit()
    return "repo1"


@pytest.fixture
async def setup_mcp(monkeypatch: pytest.MonkeyPatch, factory, repo_with_page, tmp_path: Path):
    import codex_wise.server.mcp_server as mcp_mod

    monkeypatch.setattr(mcp_mod, "_session_factory", factory)
    monkeypatch.setattr(mcp_mod, "_fts", FakeFts())
    monkeypatch.setattr(mcp_mod, "_vector_store", None)
    monkeypatch.setattr(mcp_mod, "_decision_store", None)
    monkeypatch.setattr(mcp_mod, "_repo_path", str(tmp_path))
    monkeypatch.setattr(mcp_mod, "_registry", None)
    return repo_with_page


@pytest.mark.asyncio
async def test_get_answer_retrieval_only_when_no_provider(
    setup_mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from codex_wise.server.mcp_server import get_answer

    monkeypatch.setattr(
        "codex_wise.server.mcp_server.tool_answer.resolve_llm_provider",
        lambda: ProviderResolution(provider=None),
    )

    result = await get_answer("How does authentication work?")

    assert result["answer"] == ""
    assert result["confidence"] == "low"
    assert result["fallback_targets"] == ["src/auth/service.py"]
    assert "CODEX_WISE_PROVIDER=codex_app" in result["note"]
    assert result["_meta"]["hint"].startswith("Low confidence")


@pytest.mark.asyncio
async def test_get_answer_invokes_codex_app_provider(
    setup_mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from codex_wise.server.mcp_server import get_answer

    provider = FakeProvider()
    monkeypatch.setattr(
        "codex_wise.server.mcp_server.tool_answer.resolve_llm_provider",
        lambda: ProviderResolution(
            provider=provider,
            provider_name="codex_app",
            model_name="gpt-5.4-mini",
            explicit_provider=True,
        ),
    )

    result = await get_answer("How does authentication work?")

    assert result["answer"] == "Auth is handled in src/auth/service.py."
    assert result["citations"] == ["src/auth/service.py"]
    assert provider.calls
    assert "Auth Service" in provider.calls[0]["user_prompt"]
    assert result["_meta"]["llm_provider"] == "codex_app"
    assert result["_meta"]["llm_model"] == "gpt-5.4-mini"


@pytest.mark.asyncio
async def test_get_answer_codex_app_failure_returns_retrieval_hits(
    setup_mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from codex_wise.server.mcp_server import get_answer

    provider = FakeProvider(exc=RuntimeError("socket missing"))
    monkeypatch.setattr(
        "codex_wise.server.mcp_server.tool_answer.resolve_llm_provider",
        lambda: ProviderResolution(
            provider=provider,
            provider_name="codex_app",
            model_name="gpt-5.4-mini",
            explicit_provider=True,
        ),
    )

    result = await get_answer("How does authentication work?")

    assert result["answer"] == ""
    assert result["retrieval"][0]["target_path"] == "src/auth/service.py"
    assert "Codex app-server synthesis failed" in result["note"]
    assert "socket missing" in result["_meta"]["llm_error"]


@pytest.mark.asyncio
async def test_get_answer_cache_is_scoped_by_provider_and_model(
    setup_mcp,
    factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from codex_wise.server.mcp_server import get_answer
    from codex_wise.server.mcp_server.tool_answer import _hash_question

    question = "How does authentication work?"
    async with factory() as session:
        session.add(
            AnswerCache(
                repository_id="repo1",
                question_hash=_hash_question(question),
                question=question,
                payload_json=json.dumps(
                    {
                        "answer": "stale openai answer",
                        "citations": ["old.py"],
                        "confidence": "high",
                        "fallback_targets": ["old.py"],
                        "retrieval": [],
                    }
                ),
                provider_name="openai",
                model_name="old-model",
            )
        )
        await session.commit()

    provider = FakeProvider("fresh codex answer from src/auth/service.py")
    monkeypatch.setattr(
        "codex_wise.server.mcp_server.tool_answer.resolve_llm_provider",
        lambda: ProviderResolution(
            provider=provider,
            provider_name="codex_app",
            model_name="gpt-5.4-mini",
            explicit_provider=True,
        ),
    )

    result = await get_answer(question)

    assert result["answer"] == "fresh codex answer from src/auth/service.py"
    assert provider.calls
    async with factory() as session:
        rows = (
            await session.execute(
                select(AnswerCache.provider_name, AnswerCache.model_name).where(
                    AnswerCache.repository_id == "repo1",
                    AnswerCache.question_hash == _hash_question(question),
                )
            )
        ).all()
    assert sorted(rows) == [("codex_app", "gpt-5.4-mini"), ("openai", "old-model")]
