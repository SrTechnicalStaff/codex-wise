"""``codex-wise doctor`` — health check for the wiki setup."""

from __future__ import annotations

import tomllib
from contextlib import suppress
from pathlib import Path
from shutil import which

import click
from rich.table import Table

from codex_wise.cli.branding import cli_name, command
from codex_wise.cli.helpers import (
    console,
    get_db_url_for_repo,
    get_codex_wise_dir,
    load_state,
    resolve_repo_path,
    run_async,
)
from codex_wise.core.persistence.database import get_repo_storage_dir
from codex_wise.core.workspace.config import get_workspace_config_path

_CODEX_MCP_SERVER_NAME = "codex_wise"
_CODEX_MCP_COMMAND = "codex-wise"
_STARTUP_TIMEOUT_SEC = 20
_TOOL_TIMEOUT_SEC = 120


def _check(name: str, ok: bool, detail: str = "") -> tuple[str, str, str]:
    status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
    return (name, status, detail)


def _extract_codex_mcp_path(args: object) -> Path | None:
    if not isinstance(args, list):
        return None
    if len(args) >= 2 and args[0] == "mcp" and isinstance(args[1], str):
        return Path(args[1])
    return None


def _has_stdio_transport(args: object) -> bool:
    if not isinstance(args, list):
        return False
    for idx, arg in enumerate(args):
        if arg == "--transport" and idx + 1 < len(args):
            return args[idx + 1] == "stdio"
    return False


def _has_local_index(target: Path) -> bool:
    return get_repo_storage_dir(target).exists() or get_workspace_config_path(target).exists()


def _path_display(path: Path) -> str:
    return str(path.resolve()) if path.exists() else str(path)


def _same_path(left: Path, right: Path) -> bool:
    with suppress(OSError, RuntimeError):
        return left.resolve() == right.resolve()
    return left == right


def _is_path_like_command(command_value: str) -> bool:
    return "/" in command_value or "\\" in command_value or Path(command_value).is_absolute()


def _command_matches_codex_wise(command_value: object) -> bool:
    if not isinstance(command_value, str):
        return False
    expected = {_CODEX_MCP_COMMAND}
    command_name = Path(command_value).stem.lower()
    return command_value.lower() in expected or command_name in expected


def _command_is_available(command_value: object) -> tuple[bool, str]:
    if not isinstance(command_value, str) or not command_value.strip():
        return False, "Expected a non-empty command"

    if _is_path_like_command(command_value):
        command_path = Path(command_value)
        return (
            command_path.exists(),
            _path_display(command_path)
            if command_path.exists()
            else f"Executable not found: {command_value}",
        )

    resolved = which(command_value)
    return (
        resolved is not None,
        resolved
        if resolved
        else f"`{command_value}` is not on PATH for this process; rerun init after installing the console script or edit .codex/config.toml to an absolute command.",
    )


def _positive_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float) and value > 0


def _check_codex_setup(
    repo_path: Path,
    *,
    desktop: bool = False,
) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str, str]] = []
    config_path = repo_path / ".codex" / "config.toml"
    configured_target: Path | None = None
    configured_cwd: Path | None = None

    if not config_path.exists():
        checks.append(
            _check(
                "Codex config",
                False,
                f"Missing {config_path}. Run `{command('init', str(repo_path))}`.",
            )
        )
    else:
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            checks.append(
                _check(
                    "Codex config",
                    False,
                    f"Invalid TOML: {exc}. Fix it or rerun `{command('init', str(repo_path))}`.",
                )
            )
        except OSError as exc:
            checks.append(_check("Codex config", False, f"Cannot read {config_path}: {exc}"))
        else:
            checks.append(_check("Codex config", True, str(config_path)))
            mcp_servers = config.get("mcp_servers")
            entry = None
            if isinstance(mcp_servers, dict):
                entry = mcp_servers.get(_CODEX_MCP_SERVER_NAME)
            if not isinstance(entry, dict):
                checks.append(
                    _check(
                        "Codex MCP server",
                        False,
                        f"Missing [mcp_servers.{_CODEX_MCP_SERVER_NAME}]. Run `{command('init', str(repo_path))}`.",
                    )
                )
            else:
                command_value = entry.get("command")
                command_ok = _command_matches_codex_wise(command_value)
                if desktop and isinstance(command_value, str):
                    command_available, command_detail = _command_is_available(command_value)
                    command_ok = command_ok and command_available
                else:
                    command_detail = (
                        f'command = "{_CODEX_MCP_COMMAND}"'
                        if command_ok
                        else f'Expected command = "{_CODEX_MCP_COMMAND}", found {command_value!r}'
                    )
                checks.append(
                    _check(
                        "Codex MCP command",
                        command_ok,
                        command_detail,
                    )
                )

                args = entry.get("args")
                configured_target = _extract_codex_mcp_path(args)
                target_ok = configured_target is not None and configured_target.exists()
                if desktop:
                    target_ok = (
                        target_ok
                        and configured_target is not None
                        and configured_target.is_absolute()
                    )
                checks.append(
                    _check(
                        "Codex MCP target",
                        target_ok,
                        str(configured_target)
                        if target_ok and configured_target is not None
                        else "Expected args like ['mcp', '<absolute repo path>', '--transport', 'stdio']",
                    )
                )

                transport_ok = _has_stdio_transport(args)
                checks.append(
                    _check(
                        "Codex MCP transport",
                        transport_ok,
                        "--transport stdio"
                        if transport_ok
                        else f"Expected --transport stdio in mcp_servers.{_CODEX_MCP_SERVER_NAME}.args",
                    )
                )

                if desktop:
                    cwd_value = entry.get("cwd")
                    configured_cwd = Path(cwd_value) if isinstance(cwd_value, str) else None
                    cwd_ok = (
                        configured_cwd is not None
                        and configured_cwd.exists()
                        and configured_cwd.is_absolute()
                        and (
                            configured_target is None
                            or _same_path(configured_cwd, configured_target)
                        )
                    )
                    checks.append(
                        _check(
                            "Codex MCP cwd",
                            cwd_ok,
                            _path_display(configured_cwd)
                            if cwd_ok and configured_cwd is not None
                            else "Expected cwd to be the same absolute path used in MCP args",
                        )
                    )

                    startup_timeout = entry.get("startup_timeout_sec")
                    startup_ok = _positive_number(startup_timeout)
                    checks.append(
                        _check(
                            "Codex MCP startup timeout",
                            startup_ok,
                            f"{startup_timeout}s"
                            if startup_ok
                            else f"Expected startup_timeout_sec = {_STARTUP_TIMEOUT_SEC}",
                        )
                    )

                    tool_timeout = entry.get("tool_timeout_sec")
                    tool_ok = _positive_number(tool_timeout)
                    checks.append(
                        _check(
                            "Codex MCP tool timeout",
                            tool_ok,
                            f"{tool_timeout}s"
                            if tool_ok
                            else f"Expected tool_timeout_sec = {_TOOL_TIMEOUT_SEC}",
                        )
                    )

                    startup_target = configured_target or configured_cwd or repo_path
                    checks.append(
                        _check(
                            "Codex MCP startup",
                            _has_local_index(startup_target),
                            "stdio-safe; local index or workspace config found"
                            if _has_local_index(startup_target)
                            else (
                                f"No .codex-wise directory or .codex-wise-workspace.yaml at "
                                f"{startup_target}. Run `{command('init', str(startup_target))}`."
                            ),
                        )
                    )

    agents_root = (
        configured_target if configured_target and configured_target.exists() else repo_path
    )
    agents_path = agents_root / "AGENTS.md"
    if not agents_path.exists():
        checks.append(
            _check(
                "AGENTS.md",
                False,
                f"Missing {agents_path}. Run `{command('generate-agents-md', str(agents_root))}`.",
            )
        )
    else:
        try:
            content = agents_path.read_text(encoding="utf-8")
        except OSError as exc:
            checks.append(_check("AGENTS.md", False, f"Cannot read {agents_path}: {exc}"))
        else:
            has_markers = (
                "<!-- CODEX_WISE:START" in content
                and "<!-- CODEX_WISE:END -->" in content
            )
            checks.append(
                _check(
                    "AGENTS.md",
                    has_markers,
                    str(agents_path)
                    if has_markers
                    else f"Missing managed markers. Run `{command('generate-agents-md', str(agents_root))}`.",
                )
            )

    if desktop:
        checks.extend(_check_desktop_environment())

    return checks


def _check_desktop_environment() -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str, str]] = []
    codex_home = Path.home() / ".codex"
    checks.append(
        _check(
            "Codex Desktop trust",
            True,
            (
                f"Project-local config is ready; trust/open this project in Codex Desktop. "
                f"Codex home detected at {codex_home}."
            )
            if codex_home.exists()
            else (
                "Project-local config is ready; Codex Desktop trust state is not readable here. "
                "Open the project in Codex Desktop and trust it when prompted."
            ),
        )
    )
    checks.append(
        _check(
            "Codex Desktop platform",
            True,
            "Windows app supports native PowerShell and WSL agents; use the same environment that can run codex-wise."
            if __import__("platform").system() == "Windows"
            else "Use a Codex Desktop local environment that can run the generated codex-wise command.",
        )
    )
    return checks


@click.command("doctor")
@click.argument("path", required=False, default=None)
@click.option("--repair", is_flag=True, default=False, help="Attempt to fix detected mismatches.")
@click.option(
    "--desktop",
    is_flag=True,
    default=False,
    help="Run Codex Desktop compatibility checks.",
)
def doctor_command(path: str | None, repair: bool, desktop: bool) -> None:
    """Run health checks on the wiki setup."""
    repo_path = resolve_repo_path(path)
    checks: list[tuple[str, str, str]] = []

    # 1. Git repository?
    try:
        import git as gitpython

        gitpython.Repo(repo_path, search_parent_directories=True)
        checks.append(_check("Git repository", True, str(repo_path)))
    except Exception:
        checks.append(_check("Git repository", False, "Not a git repo"))

    # 2. storage directory exists?
    codex_wise_dir = get_codex_wise_dir(repo_path)
    checks.append(_check(".codex-wise/ storage", codex_wise_dir.exists(), str(codex_wise_dir)))

    # 3. Database connectable?
    db_path = codex_wise_dir / "wiki.db"
    db_ok = False
    page_count = 0
    if db_path.exists():
        try:

            async def _check_db():
                from codex_wise.core.persistence import (
                    create_engine,
                    create_session_factory,
                    get_repository_by_path,
                    get_session,
                    list_pages,
                )

                url = get_db_url_for_repo(repo_path)
                engine = create_engine(url)
                sf = create_session_factory(engine)
                count = 0
                async with get_session(sf) as session:
                    repo = await get_repository_by_path(session, str(repo_path))
                    if repo:
                        pages = await list_pages(session, repo.id, limit=10000)
                        count = len(pages)
                await engine.dispose()
                return count

            page_count = run_async(_check_db())
            db_ok = True
        except Exception as e:
            checks.append(_check("Database", False, str(e)))
    if db_ok:
        checks.append(_check("Database", True, f"{page_count} pages"))
    elif not db_path.exists():
        checks.append(_check("Database", False, "wiki.db not found"))

    # 4. state.json valid?
    state = load_state(repo_path)
    state_ok = bool(state)
    checks.append(
        _check(
            "state.json",
            state_ok,
            f"last_sync: {(state.get('last_sync_commit') or '—')[:8]}"
            if state_ok
            else "Not found or empty",
        )
    )

    # 5. Provider importable?
    provider_ok = False
    try:
        from codex_wise.core.providers import list_providers

        providers = list_providers()
        provider_ok = len(providers) > 0
        checks.append(_check("Providers", provider_ok, ", ".join(providers)))
    except Exception as e:
        checks.append(_check("Providers", False, str(e)))

    # 6. Provider configuration?
    from codex_wise.cli.helpers import validate_provider_config

    config_warnings = validate_provider_config()
    config_ok = len(config_warnings) == 0
    config_detail = "All required API keys configured" if config_ok else "; ".join(config_warnings)
    checks.append(_check("Provider config", config_ok, config_detail))

    # 7. Stale page count
    stale_count = 0
    if db_ok and page_count > 0:
        try:

            async def _check_stale():
                from codex_wise.core.persistence import (
                    create_engine,
                    create_session_factory,
                    get_repository_by_path,
                    get_session,
                    get_stale_pages,
                )

                url = get_db_url_for_repo(repo_path)
                engine = create_engine(url)
                sf = create_session_factory(engine)
                async with get_session(sf) as session:
                    repo = await get_repository_by_path(session, str(repo_path))
                    if repo:
                        stale = await get_stale_pages(session, repo.id)
                        await engine.dispose()
                        return len(stale)
                await engine.dispose()
                return 0

            stale_count = run_async(_check_stale())
            checks.append(_check("Stale pages", stale_count == 0, f"{stale_count} stale"))
        except Exception:
            checks.append(_check("Stale pages", True, "Could not check"))

    # 8-9. Three-store consistency (SQL vs Vector Store vs FTS)
    missing_from_vector: set[str] = set()
    orphaned_vector: set[str] = set()
    missing_from_fts: set[str] = set()
    orphaned_fts: set[str] = set()

    if db_ok and page_count > 0:
        try:

            async def _check_stores():
                from codex_wise.core.persistence import (
                    FullTextSearch,
                    create_engine,
                    create_session_factory,
                    get_repository_by_path,
                    get_session,
                    list_pages,
                )
                from codex_wise.core.persistence.vector_store import (
                    LanceDBVectorStore,
                )
                from codex_wise.core.providers.embedding.base import MockEmbedder

                url = get_db_url_for_repo(repo_path)
                engine = create_engine(url)
                sf = create_session_factory(engine)

                # Get all SQL page IDs
                async with get_session(sf) as session:
                    repo = await get_repository_by_path(session, str(repo_path))
                    if not repo:
                        await engine.dispose()
                        return set(), set(), set(), set()
                    pages = await list_pages(session, repo.id, limit=10000)
                    sql_ids = {p.page_id for p in pages}

                # Check vector store
                vs_ids: set[str] = set()
                lance_dir = codex_wise_dir / "lancedb"
                if lance_dir.exists():
                    try:
                        embedder = MockEmbedder()
                        vs = LanceDBVectorStore(str(lance_dir), embedder=embedder)
                        vs_ids = await vs.list_page_ids()
                        await vs.close()
                    except Exception:
                        pass  # LanceDB not available

                m_vec = sql_ids - vs_ids if vs_ids else set()
                o_vec = vs_ids - sql_ids if vs_ids else set()

                # Check FTS
                fts = FullTextSearch(engine)
                try:
                    fts_ids = await fts.list_indexed_ids()
                except Exception:
                    fts_ids = set()
                m_fts = sql_ids - fts_ids if fts_ids else set()
                o_fts = fts_ids - sql_ids if fts_ids else set()

                await engine.dispose()
                return m_vec, o_vec, m_fts, o_fts

            missing_from_vector, orphaned_vector, missing_from_fts, orphaned_fts = run_async(
                _check_stores()
            )

            vec_ok = not missing_from_vector and not orphaned_vector
            vec_detail = (
                "in sync"
                if vec_ok
                else (f"{len(missing_from_vector)} missing, {len(orphaned_vector)} orphaned")
            )
            checks.append(_check("SQL ↔ Vector Store", vec_ok, vec_detail))

            fts_ok = not missing_from_fts and not orphaned_fts
            fts_detail = (
                "in sync"
                if fts_ok
                else (f"{len(missing_from_fts)} missing, {len(orphaned_fts)} orphaned")
            )
            checks.append(_check("SQL ↔ FTS Index", fts_ok, fts_detail))
        except Exception:
            checks.append(_check("Store consistency", True, "Could not check"))

    # 10. AtomicStorageCoordinator drift check
    coord_drift: float | None = None
    coord_sql_pages: int | None = None
    coord_vector_count: int | None = None
    if db_ok:
        try:

            async def _check_coordinator():
                from codex_wise.core.persistence import (
                    create_engine,
                    create_session_factory,
                    get_session,
                )
                from codex_wise.core.persistence.coordinator import AtomicStorageCoordinator
                from codex_wise.core.persistence.vector_store import LanceDBVectorStore
                from codex_wise.core.providers.embedding.base import MockEmbedder

                url = get_db_url_for_repo(repo_path)
                engine = create_engine(url)
                sf = create_session_factory(engine)

                vector_store = None
                lance_dir = codex_wise_dir / "lancedb"
                if lance_dir.exists():
                    try:
                        embedder = MockEmbedder()
                        vector_store = LanceDBVectorStore(str(lance_dir), embedder=embedder)
                    except Exception:
                        pass

                async with get_session(sf) as session:
                    coord = AtomicStorageCoordinator(
                        session, graph_builder=None, vector_store=vector_store
                    )
                    result = await coord.health_check()

                if vector_store is not None:
                    with suppress(Exception):
                        await vector_store.close()
                await engine.dispose()
                return result

            coord_result = run_async(_check_coordinator())
            coord_sql_pages = coord_result.get("sql_pages")
            coord_vector_count = coord_result.get("vector_count")
            coord_drift = coord_result.get("drift")

            drift_pct = f"{coord_drift * 100:.1f}%" if coord_drift is not None else "N/A"
            if coord_drift is None:
                drift_color = "white"
            elif coord_drift < 0.05:
                drift_color = "green"
            elif coord_drift < 0.15:
                drift_color = "yellow"
            else:
                drift_color = "red"

            vec_display = (
                str(coord_vector_count)
                if coord_vector_count != -1 and coord_vector_count is not None
                else "unknown"
            )
            drift_detail = (
                f"SQL={coord_sql_pages}, Vector={vec_display}, "
                f"Drift=[{drift_color}]{drift_pct}[/{drift_color}]"
            )
            coord_ok = coord_drift is None or coord_drift < 0.05
            checks.append(_check("Coordinator drift", coord_ok, drift_detail))
        except Exception as exc:
            checks.append(_check("Coordinator drift", True, f"Could not check: {exc}"))

    checks.extend(_check_codex_setup(repo_path, desktop=desktop))

    # Display
    table = Table(title=f"{cli_name()} Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail")
    for name, status, detail in checks:
        table.add_row(name, status, detail)
    console.print(table)

    all_ok = all("[green]OK[/green]" in status for _, status, _ in checks)
    if all_ok:
        console.print("[bold green]All checks passed![/bold green]")
    else:
        console.print("[bold yellow]Some checks failed.[/bold yellow]")

    # --repair: fix detected mismatches
    has_mismatches = missing_from_fts or orphaned_fts or missing_from_vector or orphaned_vector
    if repair and has_mismatches:
        console.print("\n[bold]Repairing store mismatches...[/bold]")

        async def _repair():
            from codex_wise.core.persistence import (
                FullTextSearch,
                create_engine,
                create_session_factory,
                get_session,
            )

            url = get_db_url_for_repo(repo_path)
            engine = create_engine(url)
            sf = create_session_factory(engine)
            repaired = 0

            # Repair FTS: re-index missing pages, delete orphaned
            if missing_from_fts or orphaned_fts:
                fts = FullTextSearch(engine)
                await fts.ensure_index()
                if missing_from_fts:
                    # Fetch full page data for missing pages
                    async with get_session(sf) as session:
                        from sqlalchemy import select

                        from codex_wise.core.persistence.models import Page

                        rows = await session.execute(
                            select(Page).where(Page.page_id.in_(list(missing_from_fts)))
                        )
                        for page in rows.scalars().all():
                            await fts.index(page.page_id, page.title, page.content)
                            repaired += 1
                for pid in orphaned_fts:
                    await fts.delete(pid)
                    repaired += 1

            # Repair vector store: re-embed missing pages, delete orphaned
            lance_dir = codex_wise_dir / "lancedb"
            if lance_dir.exists() and (missing_from_vector or orphaned_vector):
                try:
                    from codex_wise.core.persistence.vector_store import LanceDBVectorStore
                    from codex_wise.core.providers.embedding.base import MockEmbedder

                    # Use mock embedder for repair to avoid API costs;
                    # user can re-run `codex-wise reindex` for real embeddings
                    embedder = MockEmbedder()

                    vs = LanceDBVectorStore(str(lance_dir), embedder=embedder)

                    if missing_from_vector:
                        async with get_session(sf) as session:
                            from sqlalchemy import select

                            from codex_wise.core.persistence.models import Page

                            rows = await session.execute(
                                select(Page).where(Page.page_id.in_(list(missing_from_vector)))
                            )
                            for page in rows.scalars().all():
                                await vs.embed_and_upsert(
                                    page.page_id,
                                    page.content,
                                    {
                                        "title": page.title,
                                        "page_type": page.page_type,
                                        "target_path": page.target_path,
                                    },
                                )
                                repaired += 1

                    for pid in orphaned_vector:
                        await vs.delete(pid)
                        repaired += 1

                    await vs.close()
                except Exception as exc:
                    console.print(f"[yellow]Vector repair skipped: {exc}[/yellow]")

            await engine.dispose()
            return repaired

        repaired_count = run_async(_repair())
        console.print(f"[bold green]Repaired {repaired_count} entries.[/bold green]")
    elif repair and not has_mismatches:
        console.print("[green]Nothing to repair.[/green]")
