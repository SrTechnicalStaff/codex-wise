---
name: codex-wise-workspace-management
description: >
  Use when the user asks to manage multi-repo Codex Wise workspaces, scan a workspace,
  add/list/remove repositories, set a default repo, or update/generate workspace context.
  Covers codex-wise workspace commands.
user-invocable: false
---

# Codex Wise Workspace Management

Use this skill when the target is a parent folder containing multiple repositories.

## Core Commands

List workspace repos:

```shell
codex-wise workspace list
```

Scan for repositories:

```shell
codex-wise workspace scan
```

Add or remove a repository:

```shell
codex-wise workspace add <path>
codex-wise workspace remove <alias>
```

Set the default repository:

```shell
codex-wise workspace set-default <alias>
```

## Workspace Indexing And Updates

Initialize all detected repos when the user explicitly wants a full workspace setup:

```shell
codex-wise init . --all --index-only
```

Update workspace indexes:

```shell
codex-wise update --workspace
codex-wise status --workspace
```

Generate workspace-level Codex instructions:

```shell
codex-wise generate-agents-md --workspace
```

## Reporting

Report repo aliases, default repo, stale/current status, and any repos that were skipped or failed.
