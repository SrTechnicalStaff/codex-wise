# CLI Reference

The command is `codex-wise`.

## Setup

### `codex-wise init [PATH]`

Indexes a repo or workspace and writes Codex integration files.

```bash
codex-wise init
codex-wise init .
codex-wise init --index-only
codex-wise init --provider openai --model gpt-5.4 --yes
```

Important options:

| Flag | Description |
|---|---|
| `--provider` | LLM provider: `anthropic`, `openai`, `gemini`, `ollama`, `mock` |
| `--model` | Provider model override |
| `--embedder` | Semantic search embedder: `gemini`, `openai`, `mock` |
| `--index-only` | Parse, graph, git, dead-code, and decisions without LLM pages |
| `--exclude / -x` | Repeatable gitignore-style exclusion pattern |
| `--include-submodules` | Include git submodule directories |
| `--commit-limit` | Max commits to analyze per file |
| `--follow-renames` | Follow file history across renames |
| `--no-agents-md` | Do not write `AGENTS.md`; persists `editor_files.agents_md: false` |
| `--yes / -y` | Skip prompts |

## Codex Instructions

### `codex-wise generate-agents-md [PATH]`

Regenerates `AGENTS.md` from the current index.

```bash
codex-wise generate-agents-md
codex-wise generate-agents-md --stdout
codex-wise generate-agents-md --output /tmp/AGENTS.md
codex-wise generate-agents-md --workspace
```

## MCP

### `codex-wise mcp [PATH]`

Starts the MCP server.

```bash
codex-wise mcp --transport stdio
codex-wise mcp --transport sse --port 7338
```

`init` writes `.codex/config.toml` so Codex can start the stdio server from the project config.

## Health

### `codex-wise doctor [PATH]`

Checks the index, provider configuration, store consistency, Codex MCP config, and `AGENTS.md`.

```bash
codex-wise doctor
codex-wise doctor --desktop
codex-wise doctor --repair
```

`--desktop` adds project-local Codex Desktop checks for `.codex/config.toml`, MCP command availability, `cwd`, stdio transport, timeouts, and `AGENTS.md`.

`--repair` applies only to supported store mismatches. It does not rewrite malformed Codex config.

## Updating

### `codex-wise update [PATH]`

Updates pages and index data for changed files.

```bash
codex-wise update
codex-wise update --dry-run
codex-wise update --since main
codex-wise update --workspace
codex-wise update --repo backend
```

### `codex-wise watch [PATH]`

Runs update automatically on file changes.

```bash
codex-wise watch
codex-wise watch --workspace
codex-wise watch --debounce 5000
```

### `codex-wise hook`

Manages git hooks for post-commit updates.

```bash
codex-wise hook install
codex-wise hook install --workspace
codex-wise hook status
codex-wise hook uninstall
```

## Querying

```bash
codex-wise search "authentication"
codex-wise search "retry policy" --mode semantic
codex-wise status
codex-wise status --workspace
codex-wise dead-code
codex-wise decision list
codex-wise decision add
```

## Server

```bash
codex-wise serve
codex-wise serve --no-ui
codex-wise serve --port 8080 --ui-port 8081
```

The server exposes REST endpoints for wiki pages, graph data, search, jobs, workspace data, and generated `AGENTS.md`.
