"""``repowise doctor`` — health check for the wiki setup."""

from __future__ import annotations

import click
from rich.table import Table

from repowise.cli.helpers import (
    console,
    get_db_url_for_repo,
    get_repowise_dir,
    load_state,
    resolve_repo_path,
    run_async,
)


def _check(name: str, ok: bool, detail: str = "") -> tuple[str, str, str]:
    status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
    return (name, status, detail)


def _skip(name: str, detail: str = "") -> tuple[str, str, str]:
    return (name, "[yellow]SKIP[/yellow]", detail)


class _MetadataOnlyEmbedder:
    """Embedder stub for LanceDB metadata operations that never embed text."""

    dimensions: int = 1

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("doctor metadata checks must not create embeddings")


def _open_lancedb_metadata_store(lance_dir):
    from repowise.core.persistence.vector_store import LanceDBVectorStore

    return LanceDBVectorStore(str(lance_dir), embedder=_MetadataOnlyEmbedder())


def _build_real_embedder_for_doctor():
    from repowise.cli.commands.init_cmd import _build_embedder, _resolve_embedder

    embedder_name = _resolve_embedder(None)
    if embedder_name == "none":
        return None, embedder_name, "no semantic embedder configured"

    try:
        return _build_embedder(embedder_name), embedder_name, None
    except click.ClickException as exc:
        return None, embedder_name, str(exc)


@click.command("doctor")
@click.argument("path", required=False, default=None)
@click.option("--repair", is_flag=True, default=False, help="Attempt to fix detected mismatches.")
def doctor_command(path: str | None, repair: bool) -> None:
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

    # 2. .repowise/ exists?
    repowise_dir = get_repowise_dir(repo_path)
    checks.append(_check(".repowise/ directory", repowise_dir.exists(), str(repowise_dir)))

    # 3. Database connectable?
    db_path = repowise_dir / "wiki.db"
    db_ok = False
    page_count = 0
    if db_path.exists():
        try:

            async def _check_db():
                from repowise.core.persistence import (
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
        from repowise.core.providers import list_providers

        providers = list_providers()
        provider_ok = len(providers) > 0
        checks.append(_check("Providers", provider_ok, ", ".join(providers)))
    except Exception as e:
        checks.append(_check("Providers", False, str(e)))

    # 6. Provider configuration?
    from repowise.cli.helpers import validate_provider_config

    config_warnings = validate_provider_config()
    config_ok = len(config_warnings) == 0
    config_detail = "All required API keys configured" if config_ok else "; ".join(config_warnings)
    checks.append(_check("Provider config", config_ok, config_detail))

    # 7. Stale page count
    stale_count = 0
    if db_ok and page_count > 0:
        try:

            async def _check_stale():
                from repowise.core.persistence import (
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
            checks.append(_skip("Stale pages", "Could not check"))

    # 8-9. Three-store consistency (SQL vs Vector Store vs FTS)
    missing_from_vector: set[str] = set()
    orphaned_vector: set[str] = set()
    missing_from_fts: set[str] = set()
    orphaned_fts: set[str] = set()
    vector_checked = False
    vector_skip_detail = "semantic vector store disabled"
    fts_checked = False
    fts_skip_detail = "FTS index could not be checked"

    if db_ok and page_count > 0:
        try:

            async def _check_stores():
                from repowise.core.persistence import (
                    FullTextSearch,
                    create_engine,
                    create_session_factory,
                    get_repository_by_path,
                    get_session,
                    list_pages,
                )

                url = get_db_url_for_repo(repo_path)
                engine = create_engine(url)
                sf = create_session_factory(engine)

                # Get all SQL page IDs
                async with get_session(sf) as session:
                    repo = await get_repository_by_path(session, str(repo_path))
                    if not repo:
                        await engine.dispose()
                        return (
                            set(),
                            set(),
                            set(),
                            set(),
                            False,
                            "repository not found",
                            False,
                            "repository not found",
                        )
                    pages = await list_pages(session, repo.id, limit=10000)
                    sql_ids = {p.page_id for p in pages}

                # Check vector store
                vs_ids: set[str] = set()
                vector_store_checked = False
                vector_detail = "semantic vector store disabled (no LanceDB store)"
                lance_dir = repowise_dir / "lancedb"
                if lance_dir.exists():
                    vs = None
                    try:
                        vs = _open_lancedb_metadata_store(lance_dir)
                        vs_ids = await vs.list_page_ids()
                        vector_store_checked = True
                        vector_detail = ""
                    except Exception as exc:
                        vector_detail = f"Could not check LanceDB store: {exc}"
                    finally:
                        if vs is not None:
                            await vs.close()

                m_vec = sql_ids - vs_ids if vector_store_checked else set()
                o_vec = vs_ids - sql_ids if vector_store_checked else set()

                # Check FTS
                fts = FullTextSearch(engine)
                fts_ids: set[str] = set()
                full_text_checked = False
                full_text_detail = ""
                try:
                    fts_ids = await fts.list_indexed_ids()
                    full_text_checked = True
                except Exception as exc:
                    full_text_detail = f"Could not check FTS index: {exc}"
                m_fts = sql_ids - fts_ids if full_text_checked else set()
                o_fts = fts_ids - sql_ids if full_text_checked else set()

                await engine.dispose()
                return (
                    m_vec,
                    o_vec,
                    m_fts,
                    o_fts,
                    vector_store_checked,
                    vector_detail,
                    full_text_checked,
                    full_text_detail,
                )

            (
                missing_from_vector,
                orphaned_vector,
                missing_from_fts,
                orphaned_fts,
                vector_checked,
                vector_skip_detail,
                fts_checked,
                fts_skip_detail,
            ) = run_async(_check_stores())

            if vector_checked:
                vec_ok = not missing_from_vector and not orphaned_vector
                vec_detail = (
                    "in sync"
                    if vec_ok
                    else (f"{len(missing_from_vector)} missing, {len(orphaned_vector)} orphaned")
                )
                checks.append(_check("SQL ↔ Vector Store", vec_ok, vec_detail))
            else:
                checks.append(_skip("SQL ↔ Vector Store", vector_skip_detail))

            if fts_checked:
                fts_ok = not missing_from_fts and not orphaned_fts
                fts_detail = (
                    "in sync"
                    if fts_ok
                    else (f"{len(missing_from_fts)} missing, {len(orphaned_fts)} orphaned")
                )
                checks.append(_check("SQL ↔ FTS Index", fts_ok, fts_detail))
            else:
                checks.append(_skip("SQL ↔ FTS Index", fts_skip_detail))
        except Exception:
            checks.append(_skip("Store consistency", "Could not check"))

    # 10. AtomicStorageCoordinator drift check
    coord_drift: float | None = None
    coord_sql_pages: int | None = None
    coord_vector_count: int | None = None
    coord_graph_nodes: int | None = None
    if db_ok:
        try:

            async def _check_coordinator():
                from repowise.core.persistence import (
                    create_engine,
                    create_session_factory,
                    get_session,
                )
                from repowise.core.persistence.coordinator import AtomicStorageCoordinator

                url = get_db_url_for_repo(repo_path)
                engine = create_engine(url)
                sf = create_session_factory(engine)

                vector_store = None
                lance_dir = repowise_dir / "lancedb"
                if lance_dir.exists():
                    try:
                        vector_store = _open_lancedb_metadata_store(lance_dir)
                    except Exception:
                        pass

                async with get_session(sf) as session:
                    coord = AtomicStorageCoordinator(
                        session, graph_builder=None, vector_store=vector_store
                    )
                    result = await coord.health_check()

                if vector_store is not None:
                    try:
                        await vector_store.close()
                    except Exception:
                        pass
                await engine.dispose()
                return result

            coord_result = run_async(_check_coordinator())
            coord_sql_pages = coord_result.get("sql_pages")
            coord_vector_count = coord_result.get("vector_count")
            coord_graph_nodes = coord_result.get("graph_nodes")
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

            vec_display = str(coord_vector_count) if coord_vector_count != -1 and coord_vector_count is not None else "unknown"
            drift_detail = (
                f"SQL={coord_sql_pages}, Vector={vec_display}, "
                f"Drift=[{drift_color}]{drift_pct}[/{drift_color}]"
            )
            coord_ok = coord_drift is None or coord_drift < 0.05
            checks.append(_check("Coordinator drift", coord_ok, drift_detail))
        except Exception as exc:
            checks.append(_skip("Coordinator drift", f"Could not check: {exc}"))

    # Display
    table = Table(title="repowise Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail")
    for name, status, detail in checks:
        table.add_row(name, status, detail)
    console.print(table)

    has_failures = any("[red]FAIL[/red]" in status for _, status, _ in checks)
    has_skips = any("[yellow]SKIP[/yellow]" in status for _, status, _ in checks)
    if not has_failures and not has_skips:
        console.print("[bold green]All checks passed![/bold green]")
    elif has_failures:
        console.print("[bold yellow]Some checks failed.[/bold yellow]")
    else:
        console.print("[bold yellow]Checks completed with skipped checks.[/bold yellow]")

    # --repair: fix detected mismatches
    has_mismatches = missing_from_fts or orphaned_fts or missing_from_vector or orphaned_vector
    if repair and has_mismatches:
        console.print("\n[bold]Repairing store mismatches...[/bold]")

        async def _repair():
            from repowise.core.persistence import (
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

                        from repowise.core.persistence.models import Page

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
            lance_dir = repowise_dir / "lancedb"
            if lance_dir.exists() and (missing_from_vector or orphaned_vector):
                vs = None
                try:
                    from repowise.core.persistence.vector_store import LanceDBVectorStore

                    embedder, embedder_name, embedder_error = _build_real_embedder_for_doctor()
                    if missing_from_vector and embedder is None:
                        console.print(
                            "[yellow]Vector repair skipped for missing pages: "
                            f"{embedder_error or embedder_name}.[/yellow]"
                        )
                        missing_for_repair: set[str] = set()
                    else:
                        missing_for_repair = missing_from_vector

                    if embedder is not None:
                        vs = LanceDBVectorStore(str(lance_dir), embedder=embedder)
                    else:
                        vs = _open_lancedb_metadata_store(lance_dir)

                    if missing_for_repair:
                        async with get_session(sf) as session:
                            from sqlalchemy import select

                            from repowise.core.persistence.models import Page

                            rows = await session.execute(
                                select(Page).where(Page.page_id.in_(list(missing_for_repair)))
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

                except Exception as exc:
                    console.print(f"[yellow]Vector repair skipped: {exc}[/yellow]")
                finally:
                    if vs is not None:
                        await vs.close()

            await engine.dispose()
            return repaired

        repaired_count = run_async(_repair())
        console.print(f"[bold green]Repaired {repaired_count} entries.[/bold green]")
    elif repair and not has_mismatches:
        console.print("[green]Nothing to repair.[/green]")
