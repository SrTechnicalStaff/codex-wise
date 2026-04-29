"""AGENTS.md generator for Codex and other agent hosts."""

from __future__ import annotations

from pathlib import Path

from .base import BaseEditorFileGenerator
from .data import EditorFileData, WorkspaceEditorFileData


class AgentsMdGenerator(BaseEditorFileGenerator):
    """Generates and maintains repo-root AGENTS.md."""

    filename = "AGENTS.md"
    marker_tag = "REPOWISE"
    template_name = "agents_md.j2"
    user_placeholder = (
        "# AGENTS.md\n\n"
        "<!-- Add custom agent instructions above or below the REPOWISE markers. "
        "Repowise only replaces the managed section. -->\n"
    )

    def write(self, repo_path: Path, data: EditorFileData) -> Path:
        return super().write(repo_path, data)

    def render_full(self, repo_path: Path, data: EditorFileData) -> str:
        return super().render_full(repo_path, data)


class WorkspaceAgentsMdGenerator(BaseEditorFileGenerator):
    """Generates and maintains workspace-root AGENTS.md."""

    filename = "AGENTS.md"
    marker_tag = "REPOWISE"
    template_name = "workspace_agents_md.j2"
    user_placeholder = (
        "# AGENTS.md\n\n"
        "<!-- Workspace-level agent instructions. "
        "Repowise only replaces the managed section. -->\n"
    )

    def write(self, workspace_root: Path, data: WorkspaceEditorFileData) -> Path:  # type: ignore[override]
        return super().write(workspace_root, data)

    def render_full(self, workspace_root: Path, data: WorkspaceEditorFileData) -> str:  # type: ignore[override]
        return super().render_full(workspace_root, data)
