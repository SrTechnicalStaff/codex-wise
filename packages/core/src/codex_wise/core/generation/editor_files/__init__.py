"""Editor-file generators for Codex Wise.

Provides generators that create and maintain Codex instruction files from
already-indexed codebase data.

No LLM calls are made; all content is derived from the Codex Wise DB.
"""

from .agents_md import AgentsMdGenerator, WorkspaceAgentsMdGenerator
from .data import (
    DecisionSummary,
    EditorFileData,
    HotspotFile,
    KeyModule,
    TechStackItem,
    WorkspaceEditorFileData,
    WorkspaceRepoSummary,
)
from .fetcher import EditorFileDataFetcher

__all__ = [
    "AgentsMdGenerator",
    "DecisionSummary",
    "EditorFileData",
    "EditorFileDataFetcher",
    "HotspotFile",
    "KeyModule",
    "TechStackItem",
    "WorkspaceAgentsMdGenerator",
    "WorkspaceEditorFileData",
    "WorkspaceRepoSummary",
]
