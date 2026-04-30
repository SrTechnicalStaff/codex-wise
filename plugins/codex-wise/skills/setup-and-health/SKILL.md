---
name: codex-wise-setup-and-health
description: >
  Use when the user asks to initialize, install, set up, index, diagnose, repair, check health,
  show status, or generate AGENTS.md for Codex Wise. Covers codex-wise init, doctor, status,
  and generate-agents-md.
user-invocable: false
---

# Codex Wise Setup And Health

Use this skill to run first-time and health-check commands from inside Codex.

## Before Running Commands

Run commands from the target repository root unless the user supplies a path.

First verify the CLI is available:

```shell
codex-wise --version
```

If the command is missing, ask the user to install or fix PATH before continuing.

## First-Time Setup

For a fast, low-cost first setup, prefer:

```shell
codex-wise init --index-only
codex-wise doctor --desktop
codex-wise status
```

Use full generation only when the user asks for generated wiki pages or has configured a provider/model:

```shell
codex-wise init --yes
```

Useful variants:

```shell
codex-wise init --dry-run
codex-wise init --test-run --yes
codex-wise init --provider openai --model gpt-5.4 --yes
codex-wise init --exclude vendor/ --exclude "generated/**"
codex-wise init --no-agents-md
```

If setup is rerun after interruption, prefer:

```shell
codex-wise init --resume
```

Use `--force` only when the user intentionally wants to regenerate existing pages.

## Health And Status

Run:

```shell
codex-wise doctor
codex-wise doctor --desktop
codex-wise status
```

Use repair only when the user asks you to fix detected mismatches or the doctor output makes the repair low-risk:

```shell
codex-wise doctor --repair
```

## AGENTS.md

To refresh Codex-facing instructions:

```shell
codex-wise generate-agents-md
```

Use `--stdout` to preview without writing:

```shell
codex-wise generate-agents-md --stdout
```

For multi-repo workspace instructions:

```shell
codex-wise generate-agents-md --workspace
```

## Reporting

Summarize what ran, whether initialization succeeded, where Codex Wise wrote config/index files, and any follow-up command the user should run.
