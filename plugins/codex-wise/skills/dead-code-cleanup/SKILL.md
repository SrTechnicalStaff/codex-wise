---
name: codex-wise-dead-code-cleanup
description: >
  Use when cleaning up unused code, removing symbols, pruning files, or evaluating dead-code findings
  in a repository initialized with Codex Wise.
user-invocable: false
---

# Dead-Code Cleanup With Codex Wise

Start with `get_dead_code()` to identify indexed cleanup candidates and confidence levels.

Before removing a candidate, call `get_context(targets=[...])` and inspect any dynamic entry points, framework conventions, tests, or external API usage that may not be obvious from static analysis.

For files or symbols with dependents, call `get_risk(targets=[...])` before deleting or rewriting.

Do not delete code solely because it appears in a dead-code report. Confirm with source inspection and tests appropriate to the affected area.
