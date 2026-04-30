---
name: codex-wise-pre-modification
description: >
  Use before modifying shared modules, public APIs, persistence code, generated instructions, or high-risk files in a Codex Wise-indexed repository.
user-invocable: false
---

# Pre-Modification Checks With Codex Wise

Call `get_context(targets=[...])` for files you plan to edit. Call `get_risk(targets=[...])` before changing hotspots or shared behavior.

Codex Wise context is advisory. Read the source before editing.
