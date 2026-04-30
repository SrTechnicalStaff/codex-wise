from __future__ import annotations

from pathlib import Path

from repowise.cli.codex_config import generate_codex_mcp_table


def test_generate_codex_mcp_table_sets_codex_app_provider(tmp_path: Path) -> None:
    table = generate_codex_mcp_table(
        tmp_path,
        command_resolver=lambda _command: "C:/bin/codex-wise.exe",
    )

    assert 'env = { CODEX_WISE_PROVIDER = "codex_app"' in table
    assert 'CODEX_WISE_CODEX_TRANSPORT = "proxy"' in table
    assert 'CODEX_WISE_DOC_MODEL = "gpt-5.5"' in table
    assert 'CODEX_WISE_CODEX_REASONING_EFFORT = "medium"' in table
