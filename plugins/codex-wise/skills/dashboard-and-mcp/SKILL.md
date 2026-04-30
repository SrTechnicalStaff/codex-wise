---
name: codex-wise-dashboard-and-mcp
description: >
  Use when the user asks to start the Codex Wise dashboard, API server, web UI, or MCP server,
  or to troubleshoot MCP integration. Covers codex-wise serve and mcp.
user-invocable: false
---

# Codex Wise Dashboard And MCP

Use this skill for local UI/API startup and MCP integration checks.

## Dashboard And API

Start the dashboard:

```shell
codex-wise serve
```

Use explicit ports when needed:

```shell
codex-wise serve --port 7338 --ui-port 7339
codex-wise serve --host 127.0.0.1 --port 7338
```

Start only the API server:

```shell
codex-wise serve --no-ui
```

`serve` is long-running. If started from Codex, keep track of the terminal session and give the user the local URL.

## MCP

The app plugin points at:

```shell
codex-wise mcp --transport stdio
```

For a specific repo:

```shell
codex-wise mcp C:\path\to\repo --transport stdio
```

For web clients:

```shell
codex-wise mcp --transport sse --port 7338
```

Do not run stdio MCP manually unless debugging. In normal Codex Desktop usage, the app starts the MCP server from the plugin or project config.

## Troubleshooting

Check:

```shell
codex-wise --version
codex-wise doctor --desktop
codex-wise status
```

If the app cannot see the plugin, verify that Codex Desktop has been fully restarted after changing plugin config or PATH.
