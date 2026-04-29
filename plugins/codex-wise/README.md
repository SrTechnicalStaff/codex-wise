# Codex Wise Plugin

This plugin wires Codex Wise into Codex through a local MCP server and agent skills.

## What It Provides

- MCP server configuration for `codex-wise mcp --transport stdio`
- Skills that prefer Codex Wise context for codebase exploration, risk checks, decisions, and dead-code cleanup
- Operational skills for `init`, `doctor`, `status`, `update`, `watch`, `hook`, `reindex`, `search`, `export`, `serve`, `mcp`, `workspace`, `costs`, `augment`, `dead-code`, `decision`, and `generate-agents-md`
- Repo-local marketplace metadata in `.agents/plugins/marketplace.json`

## Local Development

Install the Codex Wise CLI in the environment where Codex launches tools:

```shell
uv tool install --editable .
```

Initialize any target repository before relying on the MCP tools:

```shell
codex-wise init
codex-wise doctor
```

The generated MCP configuration intentionally omits a fixed repository path so Codex Wise can resolve the current project when the plugin is used.

## TODO Before Publishing

Fill the remaining publisher, homepage, repository, privacy, and terms placeholders in `.codex-plugin/plugin.json`.
