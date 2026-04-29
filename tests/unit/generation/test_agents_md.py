"""Unit tests for AGENTS.md generation."""

from __future__ import annotations

import pytest

from codex_wise.core.generation.editor_files import (
    AgentsMdGenerator,
    EditorFileData,
    HotspotFile,
    KeyModule,
    TechStackItem,
)


def _make_data() -> EditorFileData:
    return EditorFileData(
        repo_name="codex-wise",
        indexed_at="2026-04-29",
        indexed_commit="abc1234",
        architecture_summary="A codebase intelligence CLI with MCP support.",
        key_modules=[KeyModule("packages/cli", "Command line entry points", 12, None)],
        entry_points=["packages/cli/src/codex_wise/cli/main.py"],
        tech_stack=[TechStackItem("Python", "3.11", "language")],
        hotspots=[HotspotFile("packages/cli/src/codex_wise/cli/main.py", 95.0, 8, None)],
        build_commands={"test": "pytest"},
        avg_confidence=0.9,
    )


@pytest.fixture
def gen() -> AgentsMdGenerator:
    return AgentsMdGenerator()


def test_render_contains_codex_context(gen: AgentsMdGenerator) -> None:
    result = gen.render(_make_data())

    assert "Codex Instructions for codex-wise" in result
    assert "Codex Wise Tool Workflow" in result
    assert "Codex Desktop or CLI" in result
    assert "get_overview" in result
    assert "get_context" in result


def test_write_creates_agents_md_at_repo_root(gen: AgentsMdGenerator, tmp_path) -> None:
    written = gen.write(tmp_path, _make_data())

    assert written == tmp_path / "AGENTS.md"
    assert written.exists()
    content = written.read_text(encoding="utf-8")
    assert "<!-- CODEX_WISE:START" in content
    assert "<!-- CODEX_WISE:END -->" in content
    assert "custom Codex instructions" in content


def test_write_preserves_user_content_and_replaces_managed_section(
    gen: AgentsMdGenerator, tmp_path
) -> None:
    target = tmp_path / "AGENTS.md"
    marker_start = gen.MARKER_START_FMT.format(tag=gen.marker_tag)
    marker_end = gen.MARKER_END_FMT.format(tag=gen.marker_tag)
    target.write_text(
        f"# Local instructions\n\nKeep this.\n\n{marker_start}\nold managed\n{marker_end}\n",
        encoding="utf-8",
    )

    gen.write(tmp_path, _make_data())
    content = target.read_text(encoding="utf-8")

    assert "Keep this." in content
    assert "old managed" not in content
    assert "codex-wise" in content
    assert content.count("<!-- CODEX_WISE:START") == 1
    assert content.count("<!-- CODEX_WISE:END -->") == 1
    assert "<!-- Codex Wise:START" not in content


def test_write_appends_when_existing_file_has_no_markers(gen: AgentsMdGenerator, tmp_path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("# Team rules\n\nRun tests before committing.\n", encoding="utf-8")

    gen.write(tmp_path, _make_data())
    content = target.read_text(encoding="utf-8")

    assert "Run tests before committing." in content
    assert "<!-- CODEX_WISE:START" in content


def test_write_is_idempotent(gen: AgentsMdGenerator, tmp_path) -> None:
    data = _make_data()
    gen.write(tmp_path, data)
    first = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    gen.write(tmp_path, data)
    second = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    assert first == second
