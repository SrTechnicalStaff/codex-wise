---
name: codex-wise-codebase-exploration
description: >
  Use when exploring, understanding, or answering questions about a codebase initialized with Codex Wise,
  indicated by .codex-wise/, .codex/config.toml with codex_wise MCP, or AGENTS.md Codex Wise markers.
user-invocable: false
---

# Codebase Exploration With Codex Wise

When Codex Wise tools are available, use them before reading broad areas of raw source.

Start with `get_overview()` for repository or workspace orientation. For specific topics, call `search_codebase(query="...")`, then fetch details with `get_context(targets=[...])`.

For focused codebase questions, prefer `get_answer(question="...")` when the answer can be grounded in indexed docs, symbols, and graph context.

For relationships between modules, use `get_dependency_path(source="...", target="...")` or `get_architecture_diagram(...)` before manually tracing imports.

If the tools report that no index exists, tell the user to run `codex-wise init`, then continue with normal source inspection.
