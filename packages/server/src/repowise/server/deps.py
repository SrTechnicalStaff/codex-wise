"""FastAPI dependency injection for repowise server.

Provides Depends() callables for:
- Database sessions (async, auto-commit/rollback)
- Vector store access
- Full-text search access
- Optional API key authentication
"""

from __future__ import annotations

import hmac
import logging
import os
from collections.abc import AsyncGenerator

from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, Request, Security
from repowise.core.persistence.database import get_session

logger = logging.getLogger(__name__)


def _env_alias(preferred: str, legacy: str, default: str | None = None) -> str | None:
    """Read Codex Wise configuration with Repowise compatibility fallback."""
    return os.environ.get(preferred) or os.environ.get(legacy) or default


_API_KEY = _env_alias("CODEX_WISE_API_KEY", "REPOWISE_API_KEY")
_CODEX_WISE_HOST = _env_alias("CODEX_WISE_HOST", "REPOWISE_HOST", "127.0.0.1")
_header_scheme = APIKeyHeader(name="Authorization", auto_error=False)

# Warn at import time if server is network-exposed without authentication
if _API_KEY is None and _CODEX_WISE_HOST in ("0.0.0.0", "::"):
    logger.warning(
        "SECURITY WARNING: Server is binding to %s without CODEX_WISE_API_KEY set. "
        "All endpoints are unauthenticated and network-accessible. "
        "Set CODEX_WISE_API_KEY or bind to 127.0.0.1.",
        _CODEX_WISE_HOST,
    )


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session with auto-commit on success, rollback on error.

    In workspace mode, routes to the correct repo's DB based on the
    ``repo_id`` path parameter when a matching session factory exists.
    """
    factory = request.app.state.session_factory

    # In workspace mode, check if the request targets a specific repo DB
    # Check both path params (e.g. /api/repos/{repo_id}/stats) and
    # query params (e.g. /api/pages?repo_id=xxx) for the repo_id
    repo_id = request.path_params.get("repo_id") or request.query_params.get("repo_id")
    if repo_id:
        ws_sessions = getattr(request.app.state, "workspace_sessions", None)
        if ws_sessions and repo_id in ws_sessions:
            factory = ws_sessions[repo_id]

    async with get_session(factory) as session:
        yield session


async def get_vector_store(request: Request):
    """Return the vector store from app state."""
    return request.app.state.vector_store


async def get_fts(request: Request):
    """Return the full-text search engine from app state."""
    return request.app.state.fts


async def get_workspace_config(request: Request):
    """Return WorkspaceConfig from app state, or None in single-repo mode."""
    return getattr(request.app.state, "workspace_config", None)


async def get_cross_repo_enricher(request: Request):
    """Return CrossRepoEnricher from app state, or None."""
    return getattr(request.app.state, "cross_repo_enricher", None)


async def verify_api_key(
    auth: str | None = Security(_header_scheme),
) -> None:
    """API key verification.

    When CODEX_WISE_API_KEY is not set and server binds to loopback, this is a
    no-op (local-only access). When binding to a non-loopback address without
    a key, requests are rejected (fail-closed for network-exposed deployments).
    When set, requests must include ``Authorization: Bearer <key>``.
    """
    if _API_KEY is None:
        if _CODEX_WISE_HOST in ("0.0.0.0", "::"):
            raise HTTPException(
                status_code=403,
                detail="Server is network-exposed but CODEX_WISE_API_KEY is not set. "
                "Set CODEX_WISE_API_KEY or bind to 127.0.0.1.",
            )
        return
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    if not hmac.compare_digest(auth[7:], _API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")
