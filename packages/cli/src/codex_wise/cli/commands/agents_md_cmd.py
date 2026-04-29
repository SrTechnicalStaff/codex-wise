"""Codex Wise generate-agents-md - generate/update AGENTS.md for Codex."""

from __future__ import annotations

import json
from pathlib import Path

import click

from codex_wise.cli.branding import command
from codex_wise.cli.helpers import (
    ensure_codex_wise_dir,
    find_workspace_root,
    get_db_url_for_repo,
    run_async,
)


@click.command("generate-agents-md")
@click.argument("path", required=False, default=None)
@click.option(
    "--output",
    "output_path",
    default=None,
    metavar="FILE",
    help="Write to a custom path (default: AGENTS.md).",
)
@click.option(
    "--stdout",
    "to_stdout",
    is_flag=True,
    default=False,
    help="Print generated content to stdout instead of writing a file.",
)
@click.option(
    "--workspace",
    "-w",
    "workspace_mode",
    is_flag=True,
    default=False,
    help=(
        "Generate a workspace-level AGENTS.md that includes cross-repo contracts, "
        "co-changes, package dependencies, and per-repo summaries."
    ),
)
def agents_md_command(
    path: str | None,
    output_path: str | None,
    to_stdout: bool,
    workspace_mode: bool,
) -> None:
    """Generate or update AGENTS.md with Codex codebase context.

    PATH defaults to the current directory. User content outside the Codex Wise
    markers is preserved; the Codex Wise-managed section is auto-updated from the
    index.
    """
    start_path = Path(path).resolve() if path else Path.cwd()

    if workspace_mode:
        try:
            content = _generate_workspace(start_path, output_path, to_stdout)
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc
        if to_stdout:
            click.echo(content, nl=False)
        return

    repo_path = start_path
    ensure_codex_wise_dir(repo_path)

    try:
        content = run_async(_generate(repo_path, output_path, to_stdout))
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if to_stdout:
        click.echo(content, nl=False)


async def _generate(
    repo_path: Path,
    output_path: str | None,
    to_stdout: bool,
) -> str | None:
    from codex_wise.core.generation.editor_files import AgentsMdGenerator, EditorFileDataFetcher
    from codex_wise.core.persistence import (
        create_engine,
        create_session_factory,
        get_session,
        init_db,
    )
    from codex_wise.core.persistence.crud import get_repository_by_path

    url = get_db_url_for_repo(repo_path)
    engine = create_engine(url)
    await init_db(engine)
    sf = create_session_factory(engine)

    try:
        async with get_session(sf) as session:
            repo = await get_repository_by_path(session, str(repo_path))
            if repo is None:
                raise click.ClickException(
                    f"Repository not found in index. Run '{command('init')}' first."
                )
            fetcher = EditorFileDataFetcher(session, repo.id, repo_path)
            data = await fetcher.fetch()
    finally:
        await engine.dispose()

    gen = AgentsMdGenerator()

    if to_stdout:
        return gen.render_full(repo_path, data)

    dest = Path(output_path).resolve() if output_path else None
    written = gen.write(dest.parent if dest else repo_path, data)
    if dest and dest != written:
        written.replace(dest)
        written = dest

    click.echo(f"AGENTS.md updated: {written}")
    return None


def _generate_workspace(
    start_path: Path,
    output_path: str | None,
    to_stdout: bool,
) -> str | None:
    """Build and write (or render) a workspace-level AGENTS.md."""
    from codex_wise.cli.commands.status_cmd import _query_repo_counts
    from codex_wise.core.generation.editor_files import (
        WorkspaceAgentsMdGenerator,
        WorkspaceEditorFileData,
        WorkspaceRepoSummary,
    )
    from codex_wise.core.workspace.config import WorkspaceConfig, get_workspace_data_dir
    from codex_wise.core.workspace.contracts import CONTRACTS_FILENAME
    from codex_wise.core.workspace.cross_repo import CROSS_REPO_EDGES_FILENAME

    ws_root = find_workspace_root(start_path)
    if ws_root is None:
        raise click.ClickException(
            "No .codex-wise-workspace.yaml found. "
            f"Run '{command('init', '<workspace-dir>')}' first."
        )

    ws_config = WorkspaceConfig.load(ws_root)
    data_dir = get_workspace_data_dir(ws_root)

    co_changes: list[dict] = []
    package_deps: list[dict] = []
    edges_file = data_dir / CROSS_REPO_EDGES_FILENAME
    if edges_file.exists():
        try:
            overlay = json.loads(edges_file.read_text(encoding="utf-8"))
            co_changes = overlay.get("co_changes", [])
            package_deps = overlay.get("package_deps", [])
        except Exception:
            pass
    co_changes = sorted(co_changes, key=lambda c: c.get("frequency", 0), reverse=True)

    contract_links: list[dict] = []
    contracts_by_type: dict[str, int] = {}
    contracts_file = data_dir / CONTRACTS_FILENAME
    if contracts_file.exists():
        try:
            contracts_data = json.loads(contracts_file.read_text(encoding="utf-8"))
            contract_links = contracts_data.get("contract_links", [])
            for contract in contracts_data.get("contracts", []):
                ctype = contract.get("contract_type") or contract.get("type", "unknown")
                contracts_by_type[ctype] = contracts_by_type.get(ctype, 0) + 1
        except Exception:
            pass

    repo_summaries: list[WorkspaceRepoSummary] = []
    overlay_data: dict = {}
    if edges_file.exists():
        try:
            overlay_data = json.loads(edges_file.read_text(encoding="utf-8"))
        except Exception:
            overlay_data = {}

    for entry in ws_config.repos:
        abs_path = (ws_root / entry.path).resolve()
        file_count, symbol_count = _query_repo_counts(abs_path)
        repo_sum = overlay_data.get("repo_summaries", {}).get(entry.alias, {})
        repo_summaries.append(
            WorkspaceRepoSummary(
                alias=entry.alias,
                is_primary=entry.is_primary,
                file_count=file_count,
                symbol_count=symbol_count,
                hotspot_count=repo_sum.get("hotspot_count", 0),
                entry_points=repo_sum.get("entry_points", []),
            )
        )

    data = WorkspaceEditorFileData(
        workspace_name=ws_root.name,
        workspace_root=str(ws_root),
        repos=repo_summaries,
        default_repo=ws_config.default_repo or "",
        co_changes=co_changes,
        package_deps=package_deps,
        contract_links=contract_links,
        contracts_by_type=contracts_by_type,
    )

    gen = WorkspaceAgentsMdGenerator()

    if to_stdout:
        return gen.render_full(ws_root, data)

    dest = Path(output_path).resolve() if output_path else None
    written = gen.write(dest.parent if dest else ws_root, data)
    if dest and dest != written:
        written.replace(dest)
        written = dest

    click.echo(f"Workspace AGENTS.md updated: {written}")
    return None
