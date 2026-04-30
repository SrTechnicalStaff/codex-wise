# User Guide

Codex Wise is a local indexing and MCP layer for coding agents. It is meant to be boring infrastructure: build an index, expose it through MCP, keep it current, and generate `AGENTS.md` from real codebase data.

## Runtime Model

```text
source repo
  -> parser + graph builder
  -> git/decision/dead-code analysis
  -> optional LLM wiki pages
  -> local database + vector index
  -> MCP tools + AGENTS.md
```

## First Run

```bash
cd /path/to/repo
codex-wise init
codex-wise doctor
```

Use `--index-only` when you want graph/git/dead-code/MCP setup without LLM-generated pages.

## Codex Project Files

`codex-wise init` writes:

```text
.codex/config.toml
AGENTS.md
```

`doctor` validates both. If `AGENTS.md` is missing or stale:

```bash
codex-wise generate-agents-md
```

## MCP Workflow

Agents should use MCP tools before broad source reads:

```text
get_overview()
get_answer(question="...")
get_context(targets=["..."])
get_risk(targets=["..."])
search_codebase(query="...")
get_why(query="...")
get_dead_code()
```

Always verify indexed summaries against source before editing.

## Updating

```bash
codex-wise update
codex-wise watch
codex-wise hook install
```

`update` refreshes generated `AGENTS.md` unless disabled in config:

```yaml
editor_files:
  agents_md: false
```

## Workspaces

```bash
cd /path/to/workspace
codex-wise init .
codex-wise status --workspace
codex-wise update --workspace
```

Workspace MCP calls can use `repo="all"` for discovery and `repo="<alias>"` for focused context.

## Server

```bash
codex-wise serve
```

Useful endpoints:

```text
GET  /api/repos
GET  /api/pages
GET  /api/repos/{repo_id}/agents-md
POST /api/repos/{repo_id}/agents-md/generate
```

## Troubleshooting

Run:

```bash
codex-wise doctor
```

Common failures:

| Check | Fix |
|---|---|
| Missing `.codex/config.toml` | Run `codex-wise init` |
| Missing `AGENTS.md` | Run `codex-wise generate-agents-md` |
| Missing database | Run `codex-wise init` |
| Stale pages | Run `codex-wise update` |
| Store drift | Run `codex-wise doctor --repair` |
