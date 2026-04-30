"""``codex-wise mcp`` — Start the MCP server for editor integration."""

from __future__ import annotations

import click

from codex_wise.cli.helpers import console, get_codex_wise_dir, resolve_repo_path
from codex_wise.core.workspace.config import get_workspace_config_path


@click.command("mcp")
@click.argument("path", required=False, default=None)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport protocol: stdio (Codex/Desktop/CLI) or sse (web clients).",
)
@click.option(
    "--port",
    type=int,
    default=7338,
    help="Port for SSE transport (default: 7338).",
)
def mcp_command(path: str | None, transport: str, port: int) -> None:
    """Start the MCP server for editor integration.

    Exposes Codex Wise tools via the MCP protocol.
    Supports both stdio (for Codex Desktop/CLI) and SSE transports.

    Examples:

        codex-wise mcp                     # stdio, current directory
        codex-wise mcp /path/to/repo       # stdio, specific repo
        codex-wise mcp --transport sse     # SSE on port 7338
    """
    repo_path = resolve_repo_path(path)

    storage_dir = get_codex_wise_dir(repo_path)
    workspace_config = get_workspace_config_path(repo_path)
    if transport != "stdio" and not storage_dir.exists() and not workspace_config.exists():
        console.print(
            f"[yellow]Warning: No .codex-wise index or workspace config found at {repo_path}.[/yellow]\n"
            "Run 'codex-wise init' first to generate context."
        )

    if transport == "sse":
        console.print(
            f"[bold green]Starting codex-wise mcp server (SSE) on port {port}...[/bold green]"
        )
    else:
        # stdio mode — no console output (it would corrupt the protocol)
        pass

    from codex_wise.server.mcp_server import run_mcp

    run_mcp(
        transport=transport,
        repo_path=str(repo_path),
        port=port,
    )
