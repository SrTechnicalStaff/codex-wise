"""Unit tests for project-scoped Codex MCP config merging."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import click
import pytest

from codex_wise.cli import codex_config


def _load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _expected_args(repo_path: Path) -> list[str]:
    return ["mcp", str(repo_path.resolve()).replace("\\", "/"), "--transport", "stdio"]


def _expected_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def test_save_project_codex_config_creates_missing_file(tmp_path: Path) -> None:
    command_path = tmp_path / "bin" / "codex-wise.exe"
    config_path = codex_config.save_project_codex_config(
        tmp_path,
        command_resolver=lambda _: str(command_path),
    )

    assert config_path == tmp_path / ".codex" / "config.toml"
    saved = _load(config_path)
    entry = saved["mcp_servers"]["codex_wise"]
    assert entry["command"] == _expected_path(command_path)
    assert entry["args"] == _expected_args(tmp_path)
    assert entry["cwd"] == _expected_path(tmp_path)
    assert entry["env"] == {
        "CODEX_WISE_PROVIDER": "codex_app",
        "CODEX_WISE_CODEX_TRANSPORT": "proxy",
        "CODEX_WISE_DOC_MODEL": "gpt-5.5",
        "CODEX_WISE_CODEX_REASONING_EFFORT": "medium",
    }
    assert entry["startup_timeout_sec"] == 20
    assert entry["tool_timeout_sec"] == 120


def test_save_project_codex_config_falls_back_to_command_name(tmp_path: Path) -> None:
    config_path = codex_config.save_project_codex_config(
        tmp_path,
        command_resolver=lambda _: None,
    )

    saved = _load(config_path)
    entry = saved["mcp_servers"]["codex_wise"]
    assert entry["command"] == "codex-wise"
    assert entry["cwd"] == _expected_path(tmp_path)


def test_save_project_codex_config_merges_with_existing_servers(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        "\n".join(
            [
                "# local codex settings",
                "[model_providers.example]",
                'name = "Example"',
                "",
                "[mcp_servers.other]",
                'command = "other"',
                'args = ["x"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    codex_config.save_project_codex_config(tmp_path, command_resolver=lambda _: None)

    text = config_path.read_text(encoding="utf-8")
    saved = tomllib.loads(text)
    assert "# local codex settings" in text
    assert saved["model_providers"]["example"]["name"] == "Example"
    assert saved["mcp_servers"]["other"]["command"] == "other"
    assert saved["mcp_servers"]["codex_wise"]["args"] == _expected_args(tmp_path)


def test_save_project_codex_config_replaces_existing_codex_wise_table(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        "\n".join(
            [
                "[mcp_servers.codex_wise]",
                'command = "old"',
                'args = ["mcp", "old-path"]',
                "",
                "[mcp_servers.other]",
                'command = "other"',
            ]
        ),
        encoding="utf-8",
    )

    codex_config.save_project_codex_config(tmp_path, command_resolver=lambda _: None)

    text = config_path.read_text(encoding="utf-8")
    saved = tomllib.loads(text)
    assert "old-path" not in text
    assert saved["mcp_servers"]["codex_wise"]["command"] == "codex-wise"
    assert saved["mcp_servers"]["codex_wise"]["args"] == _expected_args(tmp_path)
    assert saved["mcp_servers"]["other"]["command"] == "other"


def test_save_project_codex_config_rejects_invalid_existing_file(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    original = "[mcp_servers.codex_wise\ncommand = 'broken'\n"
    config_path.write_text(original, encoding="utf-8")

    with pytest.raises(click.ClickException, match=re.escape(str(config_path))):
        codex_config.save_project_codex_config(tmp_path, command_resolver=lambda _: None)

    assert config_path.read_text(encoding="utf-8") == original
