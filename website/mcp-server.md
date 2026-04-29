---
layout: default
title: MCP Server
nav_order: 5
---

# MCP Server

`codex-wise init` writes project-scoped Codex MCP config:

```toml
[mcp_servers.codex_wise]
command = "codex-wise"
args = ["mcp", "/absolute/path/to/repo", "--transport", "stdio"]
```

Manual startup:

```bash
codex-wise mcp --transport stdio
```

Workspace calls can use `repo="all"` for discovery and a repo alias for focused work.
