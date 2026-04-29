"""Unit tests for workspace-level AGENTS.md generation."""

from __future__ import annotations

import pytest

from codex_wise.core.generation.editor_files import (
    WorkspaceAgentsMdGenerator,
    WorkspaceEditorFileData,
    WorkspaceRepoSummary,
)


def _repo(
    alias: str = "api",
    *,
    is_primary: bool = True,
    entry_points: list[str] | None = None,
) -> WorkspaceRepoSummary:
    return WorkspaceRepoSummary(
        alias=alias,
        is_primary=is_primary,
        file_count=25,
        symbol_count=180,
        hotspot_count=2,
        entry_points=entry_points or ["src/main.py"],
    )


def _make_data() -> WorkspaceEditorFileData:
    return WorkspaceEditorFileData(
        workspace_name="platform",
        workspace_root="/tmp/platform",
        repos=[_repo("api"), _repo("web", is_primary=False)],
        default_repo="api",
        co_changes=[
            {
                "source_repo": "api",
                "source_file": "routes.py",
                "target_repo": "web",
                "target_file": "client.ts",
                "frequency": 4,
            }
        ],
        package_deps=[{"source_repo": "web", "target_repo": "api", "kind": "local_path"}],
        contract_links=[
            {
                "provider_repo": "api",
                "provider_file": "routes.py",
                "consumer_repo": "web",
                "consumer_file": "client.ts",
                "contract_type": "http",
                "contract_id": "GET::/health",
            }
        ],
        contracts_by_type={"http": 1},
    )


@pytest.fixture
def gen() -> WorkspaceAgentsMdGenerator:
    return WorkspaceAgentsMdGenerator()


def test_render_contains_workspace_context(gen: WorkspaceAgentsMdGenerator) -> None:
    result = gen.render(_make_data())

    assert "Codex Workspace Instructions: platform" in result
    assert "Open Codex at this workspace root" in result
    assert 'repo="all"' in result
    assert "GET::/health" in result
    assert "get_overview" in result


def test_write_creates_agents_md_at_workspace_root(
    gen: WorkspaceAgentsMdGenerator, tmp_path
) -> None:
    written = gen.write(tmp_path, _make_data())

    assert written == tmp_path / "AGENTS.md"
    assert written.exists()
    content = written.read_text(encoding="utf-8")
    assert "<!-- CODEX_WISE:START" in content
    assert "<!-- CODEX_WISE:END -->" in content
    assert "Workspace-level Codex instructions" in content


def test_write_preserves_user_content_and_is_idempotent(
    gen: WorkspaceAgentsMdGenerator, tmp_path
) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("# Workspace rules\n\nKeep local text.\n", encoding="utf-8")

    gen.write(tmp_path, _make_data())
    first = target.read_text(encoding="utf-8")
    gen.write(tmp_path, _make_data())
    second = target.read_text(encoding="utf-8")

    assert "Keep local text." in first
    assert "<!-- CODEX_WISE:START" in first
    assert first == second
