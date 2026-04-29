"""``codex-wise hook`` — manage git post-commit hooks for auto-sync."""

from __future__ import annotations

import click

from codex_wise.cli.helpers import console, find_workspace_root, resolve_repo_path


@click.group("hook")
def hook_group() -> None:
    """Manage git hooks for automatic wiki sync."""


@hook_group.command("install")
@click.argument("path", required=False, default=None)
@click.option(
    "--workspace",
    "-w",
    is_flag=True,
    default=False,
    help="Install hooks for all repos in the workspace.",
)
def hook_install(path: str | None, workspace: bool) -> None:
    """Install a post-commit hook that auto-syncs after every commit."""
    from codex_wise.cli.hooks import install

    repo_path = resolve_repo_path(path)

    if workspace:
        ws_root = find_workspace_root(repo_path)
        if ws_root is None:
            raise click.ClickException("No workspace found.")

        from codex_wise.core.workspace import WorkspaceConfig

        ws_config = WorkspaceConfig.load(ws_root)
        for entry in ws_config.repos:
            abs_path = (ws_root / entry.path).resolve()
            result = install(abs_path)
            console.print(f"  {entry.alias}: [green]{result}[/green]")
    else:
        result = install(repo_path)
        console.print(f"Post-commit hook: [green]{result}[/green]")


@hook_group.command("uninstall")
@click.argument("path", required=False, default=None)
@click.option(
    "--workspace",
    "-w",
    is_flag=True,
    default=False,
    help="Uninstall hooks from all repos in the workspace.",
)
def hook_uninstall(path: str | None, workspace: bool) -> None:
    """Remove the Codex Wise post-commit hook."""
    from codex_wise.cli.hooks import uninstall

    repo_path = resolve_repo_path(path)

    if workspace:
        ws_root = find_workspace_root(repo_path)
        if ws_root is None:
            raise click.ClickException("No workspace found.")

        from codex_wise.core.workspace import WorkspaceConfig

        ws_config = WorkspaceConfig.load(ws_root)
        for entry in ws_config.repos:
            abs_path = (ws_root / entry.path).resolve()
            result = uninstall(abs_path)
            console.print(f"  {entry.alias}: {result}")
    else:
        result = uninstall(repo_path)
        console.print(f"Post-commit hook: {result}")


@hook_group.command("status")
@click.argument("path", required=False, default=None)
@click.option(
    "--workspace",
    "-w",
    is_flag=True,
    default=False,
    help="Check hooks for all repos in the workspace.",
)
def hook_status(path: str | None, workspace: bool) -> None:
    """Check if the Codex Wise post-commit hook is installed."""
    from codex_wise.cli.hooks import status

    repo_path = resolve_repo_path(path)

    if workspace:
        ws_root = find_workspace_root(repo_path)
        if ws_root is None:
            raise click.ClickException("No workspace found.")

        from codex_wise.core.workspace import WorkspaceConfig

        ws_config = WorkspaceConfig.load(ws_root)
        for entry in ws_config.repos:
            abs_path = (ws_root / entry.path).resolve()
            result = status(abs_path)
            icon = "[green]✓[/green]" if result == "installed" else "[dim]✗[/dim]"
            console.print(f"  {icon} {entry.alias}: {result}")
    else:
        result = status(repo_path)
        icon = "[green]✓[/green]" if result == "installed" else "[dim]✗[/dim]"
        console.print(f"  {icon} post-commit: {result}")
