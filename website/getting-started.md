---
layout: default
title: Getting Started
nav_order: 2
---

# Getting Started

## Install

```bash
uv sync --all-packages
uv run codex-wise --help
```

For a persistent local command:

```bash
uv tool install --editable .
```

## Initialize

```bash
cd /path/to/repo
codex-wise init
```

For analysis-only setup:

```bash
codex-wise init --index-only
```

## Validate

```bash
codex-wise doctor
```

The Codex checks validate `.codex/config.toml`, MCP stdio args, target path, and `AGENTS.md` markers.

## Regenerate Instructions

```bash
codex-wise generate-agents-md
codex-wise generate-agents-md --workspace
```

## Workspace

```bash
cd /path/to/workspace
codex-wise init .
codex-wise status --workspace
```
