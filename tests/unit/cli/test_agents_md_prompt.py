"""Regression tests for AGENTS.md init gating."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from codex_wise.cli.commands.init_cmd import _maybe_generate_agents_md


def _silent_console() -> Console:
    return Console(file=StringIO(), force_terminal=False)


def test_maybe_generate_skips_write_when_user_opted_out(tmp_path: Path) -> None:
    (tmp_path / ".codex-wise").mkdir()

    _maybe_generate_agents_md(_silent_console(), tmp_path, no_agents_md=True)

    assert not (tmp_path / "AGENTS.md").exists()
    cfg_path = tmp_path / ".codex-wise" / "config.yaml"
    assert cfg_path.exists()
    assert "agents_md: false" in cfg_path.read_text(encoding="utf-8")


def test_maybe_generate_skips_write_when_config_disabled(tmp_path: Path) -> None:
    (tmp_path / ".codex-wise").mkdir()
    cfg_path = tmp_path / ".codex-wise" / "config.yaml"
    cfg_path.write_text("editor_files:\n  agents_md: false\n", encoding="utf-8")

    with patch("codex_wise.cli.commands.init_cmd._write_agents_md_async") as fake_write:
        _maybe_generate_agents_md(_silent_console(), tmp_path, no_agents_md=False)

    fake_write.assert_not_called()
    assert not (tmp_path / "AGENTS.md").exists()
