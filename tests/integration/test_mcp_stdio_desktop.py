"""Stdio MCP smoke tests for Codex Desktop-style project config."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def _list_stdio_tools(root: Path) -> list[str]:
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-c",
            "from codex_wise.cli.main import cli; cli()",
            "mcp",
            str(root),
            "--transport",
            "stdio",
        ],
        cwd=str(Path.cwd()),
        env={
            "PYTHONPATH": str(Path.cwd()),
            "CODEX_WISE_EMBEDDER": "mock",
        },
    )

    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        return sorted(tool.name for tool in tools.tools)


@pytest.mark.asyncio
async def test_stdio_mcp_smoke_single_repo(tmp_path: Path) -> None:
    (tmp_path / ".codex-wise").mkdir()

    tools = await _list_stdio_tools(tmp_path)

    assert "get_overview" in tools
    assert "search_codebase" in tools


@pytest.mark.asyncio
async def test_stdio_mcp_smoke_workspace_root(tmp_path: Path) -> None:
    repo = tmp_path / "api"
    (repo / ".codex-wise").mkdir(parents=True)
    (tmp_path / ".codex-wise-workspace.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "default_repo: api",
                "repos:",
                "  - path: api",
                "    alias: api",
                "    is_primary: true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    tools = await _list_stdio_tools(tmp_path)

    assert "get_overview" in tools
    assert "get_context" in tools
