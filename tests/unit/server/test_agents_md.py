"""Tests for /api/repos/{repo_id}/agents-md endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from codex_wise.core.persistence import crud
from codex_wise.core.persistence.database import get_session
from tests.unit.server.conftest import create_test_repo


async def _create_indexed_repo(client: AsyncClient, app) -> dict:
    repo = await create_test_repo(client)
    async with get_session(app.state.session_factory) as session:
        await crud.upsert_page(
            session,
            page_id="repo_overview",
            repository_id=repo["id"],
            page_type="repo_overview",
            title="Overview",
            content="This repository exposes a CLI and MCP server.",
            target_path="",
            source_hash="abc123",
            model_name="mock",
            provider_name="mock",
        )
    return repo


@pytest.mark.asyncio
async def test_get_agents_md_preview(client: AsyncClient, app) -> None:
    repo = await _create_indexed_repo(client, app)

    resp = await client.get(f"/api/repos/{repo['id']}/agents-md")

    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_name"] == "test-repo"
    assert "Codex Instructions for test-repo" in data["content"]
    assert "Codex Wise Tool Workflow" in data["content"]
    assert "Architecture" in data["sections"]


@pytest.mark.asyncio
async def test_generate_agents_md_writes_file(client: AsyncClient, app) -> None:
    repo = await _create_indexed_repo(client, app)

    resp = await client.post(f"/api/repos/{repo['id']}/agents-md/generate")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "generated"
    assert data["path"].endswith("AGENTS.md")
    content = Path(data["path"]).read_text(encoding="utf-8")
    assert "<!-- CODEX_WISE:START" in content
