# Codex Desktop

Codex Wise is configured for Codex Desktop through project-local files only:

- `.codex/config.toml` starts the codex-wise mcp server with stdio transport.
- `AGENTS.md` gives Codex project or workspace instructions.
- `.codex-wise/` or `.codex-wise-workspace.yaml` stores the local index used by MCP tools.

Run setup from the repository or workspace root:

```bash
codex-wise init
codex-wise doctor --desktop
```

Open the same root in Codex Desktop and trust the project when prompted. No global `~/.codex/config.toml` edit is required.

## Generated MCP Config

`codex-wise init` writes `.codex/config.toml` with a project-scoped server entry:

```toml
[mcp_servers.codex_wise]
command = "C:/path/to/codex-wise.exe"
args = ["mcp", "C:/path/to/project", "--transport", "stdio"]
cwd = "C:/path/to/project"
startup_timeout_sec = 20
tool_timeout_sec = 120
```

If the `codex-wise` executable cannot be resolved during init, the command falls back to `codex-wise`. In that case `codex-wise doctor --desktop` checks whether the command is available on the PATH visible to the current environment.

## Workspace Roots

For a multi-repo workspace, open Codex Desktop at the workspace root that contains `.codex-wise-workspace.yaml`, `.codex/config.toml`, and workspace `AGENTS.md`.

Workspace MCP tools can be scoped with:

```text
repo="all"
repo="<alias>"
```

## Diagnostics

Use:

```bash
codex-wise doctor --desktop
```

The Desktop check validates:

- project-local `.codex/config.toml`
- MCP command availability
- absolute MCP target path and `cwd`
- stdio transport
- timeout fields
- local index or workspace config
- `AGENTS.md` managed markers

Codex Desktop trust state is best-effort: if local app state is not readable, doctor reports a manual trust/open-project checklist instead of failing the project.

## Platform Notes

Codex Desktop stores local environment configuration under the project `.codex` folder. On Windows, the Codex app can run with native PowerShell support or WSL; use the same environment that can run the generated `codex-wise` command.

OpenAI references:

- [Codex MCP](https://developers.openai.com/codex/mcp)
- [AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Codex Desktop local environments](https://developers.openai.com/codex/app/local-environments)
- [Codex Desktop on Windows](https://developers.openai.com/codex/app/windows)
