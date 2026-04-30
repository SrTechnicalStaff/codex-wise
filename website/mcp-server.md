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
env = { CODEX_WISE_PROVIDER = "codex_app", CODEX_WISE_CODEX_TRANSPORT = "proxy", CODEX_WISE_DOC_MODEL = "gpt-5.5", CODEX_WISE_CODEX_REASONING_EFFORT = "medium" }
```

Manual startup:

```bash
codex-wise mcp --transport stdio
```

Workspace calls can use `repo="all"` for discovery and a repo alias for focused work.
