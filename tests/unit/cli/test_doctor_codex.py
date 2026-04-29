"""Codex diagnostics in doctor."""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from codex_wise.cli.codex_config import save_project_codex_config
from codex_wise.cli.commands.doctor_cmd import _check_codex_setup
from codex_wise.cli.main import cli


def _status_map(checks: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    return {name: (status, detail) for name, status, detail in checks}


def _write_agents_md(repo_path: Path) -> None:
    repo_path.joinpath("AGENTS.md").write_text(
        "\n".join(
            [
                "# AGENTS.md",
                "<!-- CODEX_WISE:START - test -->",
                "managed",
                "<!-- CODEX_WISE:END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_codex_setup_check_reports_missing_config_and_agents_md(tmp_path: Path) -> None:
    checks = _status_map(_check_codex_setup(tmp_path))

    assert "[red]FAIL[/red]" in checks["Codex config"][0]
    assert "init" in checks["Codex config"][1]
    assert "[red]FAIL[/red]" in checks["AGENTS.md"][0]
    assert "generate-agents-md" in checks["AGENTS.md"][1]


def test_codex_setup_check_rejects_malformed_toml(tmp_path: Path) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[mcp_servers.codex_wise\n", encoding="utf-8")
    _write_agents_md(tmp_path)

    checks = _status_map(_check_codex_setup(tmp_path))

    assert "[red]FAIL[/red]" in checks["Codex config"][0]
    assert "Invalid TOML" in checks["Codex config"][1]
    assert "[green]OK[/green]" in checks["AGENTS.md"][0]


def test_codex_setup_check_validates_mcp_entry(tmp_path: Path) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        "\n".join(
            [
                "[mcp_servers.codex_wise]",
                'command = "other"',
                'args = ["mcp", "C:/missing/path", "--transport", "sse"]',
            ]
        ),
        encoding="utf-8",
    )
    _write_agents_md(tmp_path)

    checks = _status_map(_check_codex_setup(tmp_path))

    assert "[red]FAIL[/red]" in checks["Codex MCP command"][0]
    assert "Expected command" in checks["Codex MCP command"][1]
    assert "[red]FAIL[/red]" in checks["Codex MCP target"][0]
    assert "[red]FAIL[/red]" in checks["Codex MCP transport"][0]


def test_codex_setup_check_accepts_valid_config(tmp_path: Path) -> None:
    save_project_codex_config(tmp_path, command_resolver=lambda _: None)
    _write_agents_md(tmp_path)

    checks = _status_map(_check_codex_setup(tmp_path))

    assert "[green]OK[/green]" in checks["Codex config"][0]
    assert "[green]OK[/green]" in checks["Codex MCP command"][0]
    assert "[green]OK[/green]" in checks["Codex MCP target"][0]
    assert "[green]OK[/green]" in checks["Codex MCP transport"][0]
    assert "[green]OK[/green]" in checks["AGENTS.md"][0]


def test_codex_setup_desktop_accepts_generated_config(tmp_path: Path) -> None:
    command_path = tmp_path / "bin" / "codex-wise.exe"
    command_path.parent.mkdir()
    command_path.write_text("", encoding="utf-8")
    (tmp_path / ".codex-wise").mkdir()
    save_project_codex_config(
        tmp_path,
        command_resolver=lambda _: str(command_path),
    )
    _write_agents_md(tmp_path)

    checks = _status_map(_check_codex_setup(tmp_path, desktop=True))

    assert "[green]OK[/green]" in checks["Codex MCP command"][0]
    assert "[green]OK[/green]" in checks["Codex MCP cwd"][0]
    assert "[green]OK[/green]" in checks["Codex MCP startup timeout"][0]
    assert "[green]OK[/green]" in checks["Codex MCP tool timeout"][0]
    assert "[green]OK[/green]" in checks["Codex MCP startup"][0]
    assert "[green]OK[/green]" in checks["Codex Desktop trust"][0]


def test_codex_setup_desktop_reports_missing_command(tmp_path: Path) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    target = str(tmp_path.resolve()).replace("\\", "/")
    config_path.write_text(
        "\n".join(
            [
                "[mcp_servers.codex_wise]",
                'command = "C:/missing/codex-wise.exe"',
                f'args = ["mcp", "{target}", "--transport", "stdio"]',
                f'cwd = "{target}"',
                "startup_timeout_sec = 20",
                "tool_timeout_sec = 120",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".codex-wise").mkdir()
    _write_agents_md(tmp_path)

    checks = _status_map(_check_codex_setup(tmp_path, desktop=True))

    assert "[red]FAIL[/red]" in checks["Codex MCP command"][0]
    assert "Executable not found" in checks["Codex MCP command"][1]


def test_codex_setup_desktop_reports_bad_cwd(tmp_path: Path) -> None:
    command_path = tmp_path / "codex-wise.exe"
    command_path.write_text("", encoding="utf-8")
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    target = str(tmp_path.resolve()).replace("\\", "/")
    command = str(command_path.resolve()).replace("\\", "/")
    config_path.write_text(
        "\n".join(
            [
                "[mcp_servers.codex_wise]",
                f'command = "{command}"',
                f'args = ["mcp", "{target}", "--transport", "stdio"]',
                'cwd = "relative/path"',
                "startup_timeout_sec = 20",
                "tool_timeout_sec = 120",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".codex-wise").mkdir()
    _write_agents_md(tmp_path)

    checks = _status_map(_check_codex_setup(tmp_path, desktop=True))

    assert "[red]FAIL[/red]" in checks["Codex MCP cwd"][0]


def test_codex_setup_desktop_accepts_workspace_root(tmp_path: Path) -> None:
    command_path = tmp_path / "codex-wise.exe"
    command_path.write_text("", encoding="utf-8")
    (tmp_path / ".codex-wise-workspace.yaml").write_text("repos: []\n", encoding="utf-8")
    save_project_codex_config(
        tmp_path,
        command_resolver=lambda _: str(command_path),
    )
    _write_agents_md(tmp_path)

    checks = _status_map(_check_codex_setup(tmp_path, desktop=True))

    assert "[green]OK[/green]" in checks["Codex MCP startup"][0]
    assert "workspace config found" in checks["Codex MCP startup"][1]


def test_doctor_uses_invoked_cli_name_in_title_and_remediation(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["doctor", str(tmp_path)], prog_name="codex-wise")

    assert result.exit_code == 0
    assert re.search(r"codex-wise Doctor", result.output)
    assert "codex-wise init" in result.output


def test_doctor_desktop_help_is_available() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["doctor", "--help"], prog_name="codex-wise")

    assert result.exit_code == 0
    assert "--desktop" in result.output
