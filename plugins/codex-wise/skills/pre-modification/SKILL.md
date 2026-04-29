---
name: codex-wise-pre-modification
description: >
  Use before modifying files in a repository initialized with Codex Wise, especially shared modules,
  public APIs, persistence code, generated editor instructions, or high-risk refactors.
user-invocable: false
---

# Pre-Modification Checks With Codex Wise

Before editing shared or unclear code, call `get_context(targets=[...])` for the files or modules involved.

For changes with non-trivial blast radius, call `get_risk(targets=[...])` and use the result to choose test scope and implementation caution.

If Codex Wise reports high coupling, recent churn, or many dependents, keep edits narrower and verify with focused tests around the affected behavior.

For trivial isolated changes, do not block progress on a full risk check. Use judgment and keep the edit local.

If Codex Wise is not initialized, note that `codex-wise init` would enable these checks and proceed with ordinary repository inspection.
