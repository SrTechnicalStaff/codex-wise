---
name: codex-wise-dead-code-cleanup
description: >
  Use when cleaning up unused code, removing symbols, pruning files, or evaluating dead-code findings
  in a repository initialized with Codex Wise. Covers get_dead_code and codex-wise dead-code.
user-invocable: false
---

# Dead-Code Cleanup With Codex Wise

Start with `get_dead_code()` to identify indexed cleanup candidates and confidence levels.

Before removing a candidate, call `get_context(targets=[...])` and inspect any dynamic entry points, framework conventions, tests, or external API usage that may not be obvious from static analysis.

For files or symbols with dependents, call `get_risk(targets=[...])` before deleting or rewriting.

Do not delete code solely because it appears in a dead-code report. Confirm with source inspection and tests appropriate to the affected area.

## CLI Dead-Code Commands

Use the CLI when the user asks to run a scan or wants formatted output:

```shell
codex-wise dead-code
codex-wise dead-code --safe-only
codex-wise dead-code --min-confidence 0.8
codex-wise dead-code --format json
codex-wise dead-code --format md
```

Use filters for focused cleanup:

```shell
codex-wise dead-code --kind unreachable_file
codex-wise dead-code --kind unused_export
codex-wise dead-code --include-internals
codex-wise dead-code --no-unused-exports
```

Treat `--include-internals` as higher-risk because it can produce more false positives.
