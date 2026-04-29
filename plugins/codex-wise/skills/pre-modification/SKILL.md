---
name: codex-wise-pre-modification
description: >
  Use before modifying shared modules, public APIs, persistence code, generated instructions, or high-risk files in a Repowise-indexed repository.
user-invocable: false
---

# Pre-Modification Checks With Repowise

Call `get_context(targets=[...])` for files you plan to edit. Call `get_risk(targets=[...])` before changing hotspots or shared behavior.

Repowise context is advisory. Read the source before editing.
