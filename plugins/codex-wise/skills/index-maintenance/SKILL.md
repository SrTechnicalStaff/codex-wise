---
name: codex-wise-index-maintenance
description: >
  Use when the user asks to update, refresh, sync, watch, reindex, maintain, or hook Codex Wise
  after code changes. Covers codex-wise update, watch, hook, and reindex.
user-invocable: false
---

# Codex Wise Index Maintenance

Use this skill when Codex Wise is already initialized and the user wants the index kept current.

## Update

For a normal incremental refresh:

```shell
codex-wise update
codex-wise status
```

Preview first when the user asks what would change:

```shell
codex-wise update --dry-run
```

Use a base ref when the user asks to sync a specific diff:

```shell
codex-wise update --since main
```

For workspace mode:

```shell
codex-wise update --workspace
codex-wise update --workspace --repo <alias>
```

## Reindex Search

Use this when pages already exist but semantic/vector search is stale or missing:

```shell
codex-wise reindex
```

Useful variants:

```shell
codex-wise reindex --embedder auto
codex-wise reindex --embedder openai
codex-wise reindex --batch-size 25
```

## Watch Mode

`watch` is long-running. Start it only when the user explicitly wants continuous syncing:

```shell
codex-wise watch
codex-wise watch --workspace
```

If running from Codex, tell the user when a long-running watch process is active and do not leave it running unless that was requested.

## Git Hooks

For automatic post-commit syncing:

```shell
codex-wise hook status
codex-wise hook install
codex-wise hook uninstall
```

Use `hook install` only after confirming the repo should auto-sync after commits.

## Reporting

After maintenance, report whether the index is current, whether AGENTS.md was refreshed, and any failures that require provider credentials or repo configuration.
