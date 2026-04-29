---
name: codex-wise-architectural-decisions
description: >
  Use when a user asks why code is structured a certain way, asks about design history,
  or when a change may conflict with recorded architecture decisions in a Codex Wise index.
user-invocable: false
---

# Architectural Decisions With Codex Wise

Use `get_why(query="...")` for why/how-history questions and design rationale.

When the question is path-specific, combine `get_why(query="...")` with `get_context(targets=[...])` so the answer includes both recorded decisions and current implementation context.

Separate recorded decision evidence from your own inference. If Codex Wise returns no relevant decision, say that directly and continue from source context.

Before changing a pattern that appears intentional, check for related decisions and mention any conflict or missing rationale.
