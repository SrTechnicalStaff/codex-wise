---
name: codex-wise-dead-code-cleanup
description: >
  Use when evaluating indexed dead-code findings in a Codex Wise repository.
user-invocable: false
---

# Dead-Code Cleanup With Codex Wise

Dead-code findings are opt-in cleanup candidates, not deletion authority.

Start with `get_dead_code(min_confidence=0.8, safe_only=true)`. Confirm each candidate from source, runtime behavior, framework conventions, and generated-code patterns before deleting anything.
