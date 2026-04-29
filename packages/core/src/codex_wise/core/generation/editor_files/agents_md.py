"""AGENTS.md generators for Codex project instructions."""

from __future__ import annotations

from pathlib import Path

from .base import BaseEditorFileGenerator
from .data import EditorFileData, WorkspaceEditorFileData


class AgentsMdGenerator(BaseEditorFileGenerator):
    """Generates and maintains AGENTS.md at the repository root."""

    filename = "AGENTS.md"
    marker_tag = "CODEX_WISE"
    template_name = "agents_md.j2"
    user_placeholder = (
        "# AGENTS.md\n\n"
        "<!-- Add your custom Codex instructions above or below the managed section. "
        "Codex Wise will never modify anything outside the managed markers. -->\n"
    )

    def write(self, repo_path: Path, data: EditorFileData) -> Path:
        """Write to <repo_path>/AGENTS.md."""
        repo_path.mkdir(parents=True, exist_ok=True)
        return super().write(repo_path, data)


class WorkspaceAgentsMdGenerator(BaseEditorFileGenerator):
    """Generates and maintains workspace-level AGENTS.md."""

    filename = "AGENTS.md"
    marker_tag = "CODEX_WISE"
    template_name = "workspace_agents_md.j2"
    user_placeholder = (
        "# AGENTS.md\n\n"
        "<!-- Workspace-level Codex instructions. "
        "Codex Wise will never modify anything outside the managed markers. -->\n"
    )

    def write(self, workspace_root: Path, data: WorkspaceEditorFileData) -> Path:  # type: ignore[override]
        """Write to <workspace_root>/AGENTS.md."""
        workspace_root.mkdir(parents=True, exist_ok=True)
        return super().write(workspace_root, data)
