---
name: codex-wise-architectural-decisions
description: >
  Use when a user asks why code is structured a certain way, asks about design history,
  or when a change may conflict with recorded architecture decisions in a Codex Wise index.
  Covers get_why and codex-wise decision commands.
user-invocable: false
---

# Architectural Decisions With Codex Wise

Use `get_why(query="...")` for why/how-history questions and design rationale when MCP tools are available.

When the question is path-specific, combine `get_why(query="...")` with `get_context(targets=[...])` so the answer includes both recorded decisions and current implementation context.

Separate recorded decision evidence from your own inference. If Codex Wise returns no relevant decision, say that directly and continue from source context.

Before changing a pattern that appears intentional, check for related decisions and mention any conflict or missing rationale.

## CLI Decision Commands

Use CLI commands when the user asks to list, add, show, confirm, deprecate, dismiss, or inspect decision health:

```shell
codex-wise decision list
codex-wise decision health
codex-wise decision show <id>
codex-wise decision add
codex-wise decision confirm <id>
codex-wise decision deprecate <id>
codex-wise decision dismiss <id>
```

Interactive commands such as `decision add` may prompt for input. If running from Codex, explain the prompts and collect needed values before starting when possible.
