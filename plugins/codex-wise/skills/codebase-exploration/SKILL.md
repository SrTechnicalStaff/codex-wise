---
name: codex-wise-codebase-exploration
description: >
  Use when exploring, understanding, or answering questions about a repository initialized with Repowise/Codex Wise.
user-invocable: false
---

# Codebase Exploration With Repowise

Use Repowise MCP tools before broad source inspection when they are available.

Start with `get_overview()`. For focused code context, call `get_context(targets=[...])`. For discovery, use `search_codebase(query="...")`, then verify against source before editing.

If no index exists, tell the user to run `repowise init --index-only`, then continue from source.
