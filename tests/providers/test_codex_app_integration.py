from __future__ import annotations

import os

import pytest

from repowise.core.providers.llm.codex_app import CodexAppProvider


@pytest.mark.asyncio
async def test_real_codex_app_server_proxy_tiny_synthesis() -> None:
    if os.environ.get("CODEX_WISE_TEST_CODEX_APP_SERVER") != "1":
        pytest.skip("Set CODEX_WISE_TEST_CODEX_APP_SERVER=1 to run real Codex app-server test.")

    provider = CodexAppProvider(
        model=os.environ.get("CODEX_WISE_TEST_CODEX_MODEL") or None,
        transport=os.environ.get("CODEX_WISE_CODEX_TRANSPORT") or "proxy",
        timeout_seconds=os.environ.get("CODEX_WISE_CODEX_TIMEOUT_SECONDS") or 60,
    )

    response = await provider.generate(
        "Return terse plain text only.",
        "Reply with exactly: pong",
        max_tokens=16,
    )

    assert "pong" in response.content.lower()
