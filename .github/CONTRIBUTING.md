# Contributing

## Local Setup

```bash
uv sync --all-packages
npm install
uv run pytest
npm --workspace packages/web run type-check
```

## Workflow

- Keep changes focused.
- Add or update tests for behavior changes.
- Run Python and web checks before opening a PR.
- Use `codex-wise` in user-facing examples.

## Project Layout

```text
packages/core      indexing, graph, generation, persistence
packages/cli       command-line interface
packages/server    FastAPI, MCP, webhooks, jobs
packages/web       Next.js dashboard
tests              unit and integration tests
docs               operational docs and roadmap
```
