# MCP Tools

Codex Wise exposes a small MCP tool set for codebase orientation, search, risk checks, rationale lookup, and cleanup review.

Start the server manually:

```bash
codex-wise mcp --transport stdio
```

`codex-wise init` also writes project-scoped Codex config to `.codex/config.toml`.

## Tools

| Tool | Primary Use |
|---|---|
| `get_overview` | Repo or workspace orientation |
| `get_answer` | Focused Q&A from indexed docs |
| `get_context` | File/module/symbol context before edits |
| `search_codebase` | Semantic discovery |
| `get_risk` | Blast radius and hotspot checks |
| `get_why` | Architectural decisions and rationale |
| `get_dead_code` | Conservative cleanup candidates |

## Recommended Flow

1. Start unfamiliar work with `get_overview()`.
2. Use `get_answer(question="...")` for direct questions.
3. Use `get_context(targets=[...])` before reading or editing unfamiliar files.
4. Use `get_risk(targets=[...])` before modifying hotspots, shared modules, or public APIs.
5. Use `search_codebase(query="...")` when you need to discover relevant code.
6. Use `get_why(query="...")` before structural changes.
7. Use `get_dead_code()` before removal work.

## Workspace Scope

Workspace tools accept `repo` where supported:

```text
repo="all"
repo="api"
repo="frontend"
```

Use `repo="all"` for broad workspace discovery, then narrow to a specific alias before edits.

## Tool Details

### `get_overview`

Returns architecture summary, modules, entry points, tech stack, hotspots, and workspace summaries.

### `get_answer`

Parameters:

| Parameter | Required | Description |
|---|---:|---|
| `question` | yes | Natural-language codebase question |
| `repo` | no | Workspace repo alias |

Use this before manual search when the question can be answered from indexed pages.

### `get_context`

Parameters:

| Parameter | Required | Description |
|---|---:|---|
| `targets` | yes | Paths, modules, or symbols |
| `include` | no | Optional context such as callers, callees, metrics, community, or source |
| `compact` | no | Compact output by default |
| `repo` | no | Workspace repo alias or `all` where supported |

Use this before edits.

### `search_codebase`

Parameters:

| Parameter | Required | Description |
|---|---:|---|
| `query` | yes | Natural-language search query |
| `repo` | no | Workspace repo alias or `all` |

Use this for discovery when you do not know the target path.

### `get_risk`

Parameters:

| Parameter | Required | Description |
|---|---:|---|
| `targets` | no | Files to assess |
| `changed_files` | no | Proposed changeset for blast-radius analysis |
| `repo` | no | Workspace repo alias |

Use this before modifying files that are hot, shared, or externally visible.

### `get_why`

Parameters:

| Parameter | Required | Description |
|---|---:|---|
| `query` | no | Natural-language query or file path |
| `repo` | no | Workspace repo alias |

Use this for architectural decisions, tradeoffs, stale decision review, and governed files.

### `get_dead_code`

Parameters:

| Parameter | Required | Description |
|---|---:|---|
| `min_confidence` | no | Minimum confidence |
| `include_internals` | no | Include private/underscore symbols |
| `repo` | no | Workspace repo alias or `all` |

Use this to review cleanup candidates. Treat findings as candidates unless `safe_to_delete` is true and source verification confirms it.

