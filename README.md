# Codex Wise

Codex Wise builds a local codebase intelligence layer for Codex and other MCP-capable coding agents. It indexes source, git history, generated wiki pages, architectural decisions, and dead-code findings, then exposes that context through MCP tools and generated `AGENTS.md` instructions.

## What It Creates

After `codex-wise init`, a project can contain:

| Artifact | Purpose |
|---|---|
| Local index directory | SQLite index, settings, sync state, and vector data |
| `.codex/config.toml` | Project-scoped Codex MCP server config |
| `AGENTS.md` | Codex instructions generated from the current index |
| `.mcp.json` | Compatibility MCP config for clients that read project MCP JSON |

## Install

From this checkout:

```bash
uv sync --all-packages
uv run codex-wise --version
```

For an editable local CLI:

```bash
uv tool install --editable .
codex-wise --help
```

## Initialize A Repository

```bash
cd /path/to/repo
codex-wise init
```

Useful variants:

```bash
codex-wise init --index-only
codex-wise init --provider openai --model gpt-5.4 --yes
codex-wise init --exclude vendor/ --exclude "generated/**"
codex-wise init --no-agents-md
```

`--index-only` skips LLM page generation and still builds the graph, git metadata, dead-code findings, MCP config, and `AGENTS.md` when possible.

## Initialize A Workspace

From a parent directory containing multiple git repositories:

```bash
cd /path/to/workspace
codex-wise init .
```

Workspace mode scans for repositories, indexes selected repos, runs cross-repo analysis, writes per-repo Codex MCP config, and writes a workspace-level `AGENTS.md`.

## Use With Codex

The project config written by `init` looks like:

```toml
[mcp_servers.codex_wise]
command = "codex-wise"
args = ["mcp", "/absolute/path/to/repo", "--transport", "stdio"]
```

Use `codex-wise doctor` to validate that this config, the target path, stdio transport, and `AGENTS.md` markers are present.

```bash
codex-wise doctor
codex-wise generate-agents-md
codex-wise mcp --transport stdio
```

## Core MCP Tools

| Tool | Use |
|---|---|
| `get_overview()` | Orient on a repo or workspace |
| `get_answer(question="...")` | Ask a focused codebase question |
| `get_context(targets=[...])` | Fetch docs, symbols, ownership, and related context before edits |
| `get_risk(targets=[...])` | Check blast radius before modifying hotspots or shared modules |
| `search_codebase(query="...")` | Locate relevant files/modules by topic |
| `get_why(query="...")` | Find architectural decisions and rationale |
| `get_dead_code()` | Review cleanup candidates |

## Keep The Index Current

```bash
codex-wise update
codex-wise update --workspace
codex-wise watch
codex-wise hook install
```

`update` also refreshes `AGENTS.md` unless `editor_files.agents_md: false` is set in the project config.

## Local Dashboard And API

```bash
codex-wise serve
codex-wise serve --no-ui
```

The API exposes preview/write endpoints for generated editor instruction files:

```text
GET  /api/repos/{repo_id}/agents-md
POST /api/repos/{repo_id}/agents-md/generate
```

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [CLI Reference](docs/CLI_REFERENCE.md)
- [MCP Tools](docs/MCP_TOOLS.md)
- [Workspaces](docs/WORKSPACES.md)
- [Roadmap](docs/ROADMAP.md)
