---
layout: home
title: Home
nav_order: 1
---

# Codex Wise

Operational codebase context for Codex.

Codex Wise indexes a repository or workspace, writes project-scoped Codex MCP config, and generates `AGENTS.md` from the current codebase index.

## Start

```bash
uv tool install --editable .
codex-wise init
codex-wise doctor
```

## What It Writes

| File | Purpose |
|---|---|
| `.codex/config.toml` | Codex MCP server entry |
| `AGENTS.md` | Project instructions generated from the index |
| Local index directory | Generated database, config, state, and vector data |

## References

- [Getting Started](getting-started)
- [CLI Reference](cli-reference)
- [MCP Server](mcp-server)
- [Configuration](configuration)
