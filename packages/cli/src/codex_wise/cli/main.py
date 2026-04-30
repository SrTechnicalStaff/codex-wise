"""Codex Wise CLI — codebase intelligence for developers and AI."""

from __future__ import annotations

import click

from codex_wise.cli import __version__
from codex_wise.cli.branding import cli_name
from codex_wise.cli.commands.agents_md_cmd import agents_md_command
from codex_wise.cli.commands.augment_cmd import augment_command
from codex_wise.cli.commands.costs_cmd import costs_command
from codex_wise.cli.commands.dead_code_cmd import dead_code_command
from codex_wise.cli.commands.decision_cmd import decision_group
from codex_wise.cli.commands.doctor_cmd import doctor_command
from codex_wise.cli.commands.export_cmd import export_command
from codex_wise.cli.commands.hook_cmd import hook_group
from codex_wise.cli.commands.init_cmd import init_command
from codex_wise.cli.commands.mcp_cmd import mcp_command
from codex_wise.cli.commands.reindex_cmd import reindex_command
from codex_wise.cli.commands.search_cmd import search_command
from codex_wise.cli.commands.serve_cmd import serve_command
from codex_wise.cli.commands.status_cmd import status_command
from codex_wise.cli.commands.update_cmd import update_command
from codex_wise.cli.commands.watch_cmd import watch_command
from codex_wise.cli.commands.workspace_cmd import workspace_group


def _version_callback(
    ctx: click.Context,
    _param: click.Parameter,
    value: bool,
) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"{cli_name()}, version {__version__}")
    ctx.exit()


@click.group()
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_version_callback,
    help="Show the version and exit.",
)
def cli() -> None:
    """Codebase intelligence for developers and AI."""


cli.add_command(augment_command)
cli.add_command(init_command)
cli.add_command(agents_md_command)
cli.add_command(costs_command)
cli.add_command(update_command)
cli.add_command(dead_code_command)
cli.add_command(decision_group)
cli.add_command(search_command)
cli.add_command(export_command)
cli.add_command(hook_group)
cli.add_command(status_command)
cli.add_command(doctor_command)
cli.add_command(watch_command)
cli.add_command(serve_command)
cli.add_command(mcp_command)
cli.add_command(reindex_command)
cli.add_command(workspace_group)
