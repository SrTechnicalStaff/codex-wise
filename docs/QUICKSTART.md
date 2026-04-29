# Quickstart

This guide gets the working Codex integration online: local index, Codex MCP config, and generated `AGENTS.md`.

## 1. Install

From this repository:

```bash
uv sync --all-packages
uv run codex-wise --help
```

For a persistent editable command:

```bash
uv tool install --editable .
codex-wise --version
```

## 2. Set A Provider Key

Full documentation generation needs one provider key:

```bash
export OPENAI_API_KEY="sk-..."
# or
export GEMINI_API_KEY="..."
# or
export ANTHROPIC_API_KEY="..."
```

PowerShell:

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

No key is required for analysis-only mode.

## 3. Initialize

```bash
cd /path/to/repo
codex-wise init
```

Analysis-only:

```bash
codex-wise init --index-only
```

Non-interactive example:

```bash
codex-wise init --provider openai --model gpt-5.4 --yes
```

## 4. Verify Codex Setup

```bash
codex-wise doctor
codex-wise doctor --desktop
```

The Codex section checks:

- `.codex/config.toml`
- `[mcp_servers.codex_wise]`
- command, `cwd`, timeout fields, and stdio transport
- configured repo/workspace path
- `AGENTS.md` and managed markers

For Codex Desktop-specific setup, see [Codex Desktop](CODEX_DESKTOP.md).

## 5. Use MCP

The MCP server is configured for Codex in `.codex/config.toml`. To run it manually:

```bash
codex-wise mcp --transport stdio
```

Common tool flow:

```text
get_overview()
get_context(targets=["path/or/module"])
get_risk(targets=["path/to/file"])
search_codebase(query="topic")
get_why(query="decision or file")
get_dead_code()
```

## 6. Keep It Current

```bash
codex-wise update
codex-wise watch
codex-wise hook install
```

`update` refreshes `AGENTS.md` by default. To disable that:

```bash
codex-wise init --no-agents-md
```

or set:

```yaml
editor_files:
  agents_md: false
```

## Workspace Mode

```bash
cd /path/to/workspace
codex-wise init .
codex-wise status --workspace
codex-wise update --workspace
```

Workspace `AGENTS.md` supports MCP calls scoped with `repo="all"` or `repo="<alias>"`.
