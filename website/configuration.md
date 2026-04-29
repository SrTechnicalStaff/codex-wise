---
layout: default
title: Configuration
nav_order: 6
---

# Configuration

Primary project files:

```text
.codex/config.toml
AGENTS.md
local index directory
```

Provider keys are read from the environment or saved local env file. Run `codex-wise doctor` to verify the active setup.

Common options:

```bash
codex-wise init --provider openai --model gpt-5.4
codex-wise init --embedder openai
codex-wise init --exclude vendor/
codex-wise init --no-agents-md
```
