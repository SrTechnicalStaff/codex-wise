# Workspaces

Workspace mode indexes multiple git repositories from one parent directory and serves them through one MCP process.

## Initialize

```bash
cd /path/to/workspace
codex-wise init .
```

The init flow scans for git repositories, prompts for selection, chooses a default repo, indexes each selected repo, and writes workspace-level `AGENTS.md`.

## Commands

```bash
codex-wise status --workspace
codex-wise update --workspace
codex-wise update --repo backend
codex-wise watch --workspace
codex-wise hook install --workspace
```

## MCP Scope

Workspace tools support repo scoping where applicable:

```text
repo="all"
repo="backend"
repo="frontend"
```

Use `repo="all"` for broad discovery. Use a specific alias before making file-level decisions.

## Generated Instructions

Workspace `AGENTS.md` includes:

- repo aliases and default repo
- entry points
- cross-repo contracts
- cross-repo co-change pairs
- package dependency links
- MCP workflow reminders

Regenerate it with:

```bash
codex-wise generate-agents-md --workspace
```
