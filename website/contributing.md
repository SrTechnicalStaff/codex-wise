---
layout: default
title: Contributing
nav_order: 9
---

# Contributing

Use the local workspace commands:

```bash
uv sync --all-packages
uv run pytest -q
uv run ruff check .
```

Keep Codex-facing work focused on the apparatus: project config, MCP behavior, generated `AGENTS.md`, diagnostics, and update flows.

