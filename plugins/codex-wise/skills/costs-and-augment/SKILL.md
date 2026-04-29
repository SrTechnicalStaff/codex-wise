---
name: codex-wise-costs-and-augment
description: >
  Use when the user asks about Codex Wise LLM costs, cost history, spending by model/day/operation,
  or AI agent tool-call augmentation with graph context. Covers codex-wise costs and augment.
user-invocable: false
---

# Codex Wise Costs And Augment

Use this skill for cost reporting and hook-mode augmentation.

## Costs

Show cost history:

```shell
codex-wise costs
```

Useful filters:

```shell
codex-wise costs --since 2026-01-01
codex-wise costs --by operation
codex-wise costs --by model
codex-wise costs --by day
codex-wise costs --repo-path C:\path\to\repo
```

If there are no costs, the repo may have been initialized with `--index-only` or no LLM-backed generation has run.

## Augment

`augment` is intended for agent hook mode:

```shell
codex-wise augment
```

Use it only when the user is wiring Codex Wise into a hook pipeline or asks to enrich AI agent tool calls with graph context. For normal Codex Desktop usage, prefer MCP tools and the other Codex Wise skills.

## Reporting

Summarize totals and grouping. For augment, explain whether it is being run interactively, configured as a hook, or only inspected.
