"""Unit tests for CLI commands using CliRunner."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from codex_wise.cli import __version__
from codex_wise.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# Basic CLI tests
# ---------------------------------------------------------------------------


class TestCliBasics:
    def test_codex_wise_version(self, runner):
        result = runner.invoke(cli, ["--version"], prog_name="codex-wise")
        assert result.exit_code == 0
        assert "codex-wise" in result.output
        assert __version__ in result.output

    def test_codex_wise_help(self, runner):
        result = runner.invoke(cli, ["--help"], prog_name="codex-wise")
        assert result.exit_code == 0
        assert "Usage: codex-wise" in result.output

    def test_codex_wise_console_script_alias(self):
        pyproject = Path(__file__).parents[3] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        assert data["project"]["scripts"]["codex-wise"] == "codex_wise.cli.main:cli"

    def test_codex_wise_import_namespace_alias(self):
        from codex_wise.cli.main import cli as native_cli

        assert native_cli is cli

    def test_init_help(self, runner):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "--dry-run" in result.output
        assert "--skip-tests" in result.output
        assert "--no-agents-md" in result.output

    def test_update_help(self, runner):
        result = runner.invoke(cli, ["update", "--help"])
        assert result.exit_code == 0
        assert "--since" in result.output

    def test_generate_agents_md_help(self, runner):
        result = runner.invoke(cli, ["generate-agents-md", "--help"])
        assert result.exit_code == 0
        assert "--stdout" in result.output
        assert "--output" in result.output
        assert "--workspace" in result.output

    def test_search_help(self, runner):
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output

    def test_export_help(self, runner):
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output

    def test_status_help(self, runner):
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_doctor_help(self, runner):
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "--desktop" in result.output

    def test_watch_help(self, runner):
        result = runner.invoke(cli, ["watch", "--help"])
        assert result.exit_code == 0
        assert "--debounce" in result.output


class TestAgentsMdCommand:
    def test_generate_agents_md_stdout(self, runner, tmp_path, monkeypatch):
        from codex_wise.cli.commands import agents_md_cmd

        async def fake_generate(repo_path, output_path, to_stdout):
            assert repo_path == tmp_path.resolve()
            assert output_path is None
            assert to_stdout is True
            return "AGENTS output"

        monkeypatch.setattr(agents_md_cmd, "_generate", fake_generate)

        result = runner.invoke(cli, ["generate-agents-md", str(tmp_path), "--stdout"])

        assert result.exit_code == 0
        assert result.output == "AGENTS output"

    def test_generate_agents_md_output(self, runner, tmp_path, monkeypatch):
        from codex_wise.cli.commands import agents_md_cmd

        output = tmp_path / "custom.md"
        seen = {}

        async def fake_generate(repo_path, output_path, to_stdout):
            seen["repo_path"] = repo_path
            seen["output_path"] = output_path
            seen["to_stdout"] = to_stdout
            return None

        monkeypatch.setattr(agents_md_cmd, "_generate", fake_generate)

        result = runner.invoke(
            cli,
            ["generate-agents-md", str(tmp_path), "--output", str(output)],
        )

        assert result.exit_code == 0
        assert seen == {
            "repo_path": tmp_path.resolve(),
            "output_path": str(output),
            "to_stdout": False,
        }

    def test_generate_agents_md_workspace_stdout(self, runner, tmp_path, monkeypatch):
        from codex_wise.cli.commands import agents_md_cmd

        def fake_generate_workspace(start_path, output_path, to_stdout):
            assert start_path == tmp_path.resolve()
            assert output_path is None
            assert to_stdout is True
            return "Workspace AGENTS output"

        monkeypatch.setattr(
            agents_md_cmd,
            "_generate_workspace",
            fake_generate_workspace,
        )

        result = runner.invoke(
            cli,
            ["generate-agents-md", str(tmp_path), "--workspace", "--stdout"],
        )

        assert result.exit_code == 0
        assert result.output == "Workspace AGENTS output"


# ---------------------------------------------------------------------------
# Stub commands
# ---------------------------------------------------------------------------


class TestStubs:
    def test_serve_help(self, runner):
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_mcp_help(self, runner):
        result = runner.invoke(cli, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "--transport" in result.output
        assert "stdio" in result.output

    def test_mcp_accepts_workspace_root_without_stdio_warning(self, runner, tmp_path, monkeypatch):
        import codex_wise.server.mcp_server as mcp_server

        (tmp_path / ".codex-wise-workspace.yaml").write_text("repos: []\n", encoding="utf-8")
        seen = {}

        def fake_run_mcp(*, transport, repo_path, port):
            seen["transport"] = transport
            seen["repo_path"] = repo_path
            seen["port"] = port

        monkeypatch.setattr(mcp_server, "run_mcp", fake_run_mcp)

        result = runner.invoke(cli, ["mcp", str(tmp_path), "--transport", "stdio"])

        assert result.exit_code == 0
        assert "Warning:" not in result.output
        assert seen == {
            "transport": "stdio",
            "repo_path": str(tmp_path.resolve()),
            "port": 7338,
        }

    def test_mcp_stdio_does_not_print_missing_index_warning(
        self,
        runner,
        tmp_path,
        monkeypatch,
    ):
        import codex_wise.server.mcp_server as mcp_server

        seen = {}

        def fake_run_mcp(*, transport, repo_path, port):
            seen["transport"] = transport
            seen["repo_path"] = repo_path
            seen["port"] = port

        monkeypatch.setattr(mcp_server, "run_mcp", fake_run_mcp)

        result = runner.invoke(cli, ["mcp", str(tmp_path), "--transport", "stdio"])

        assert result.exit_code == 0
        assert result.output == ""
        assert seen == {
            "transport": "stdio",
            "repo_path": str(tmp_path.resolve()),
            "port": 7338,
        }

    def test_mcp_sse_keeps_missing_index_warning(self, runner, tmp_path, monkeypatch):
        import codex_wise.server.mcp_server as mcp_server

        seen = {}

        def fake_run_mcp(*, transport, repo_path, port):
            seen["transport"] = transport
            seen["repo_path"] = repo_path
            seen["port"] = port

        monkeypatch.setattr(mcp_server, "run_mcp", fake_run_mcp)

        result = runner.invoke(cli, ["mcp", str(tmp_path), "--transport", "sse"])

        assert result.exit_code == 0
        assert "Warning: No .codex-wise index or workspace config found" in result.output
        assert "Starting codex-wise mcp server" in result.output
        assert seen == {
            "transport": "sse",
            "repo_path": str(tmp_path.resolve()),
            "port": 7338,
        }


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    def test_init_nonexistent_path(self, runner, tmp_path):
        bad_path = str(tmp_path / "nonexistent")
        result = runner.invoke(cli, ["init", bad_path])
        assert result.exit_code != 0

    def test_init_no_provider(self, runner, tmp_path, monkeypatch):
        """init with no provider configured should error."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.delenv("CODEX_WISE_PROVIDER", raising=False)
        result = runner.invoke(cli, ["init", str(tmp_path)])
        assert result.exit_code != 0

    def test_status_no_codex_wise_dir(self, runner, tmp_path):
        result = runner.invoke(cli, ["status", str(tmp_path)], prog_name="codex-wise")
        assert result.exit_code == 0
        assert "No .codex-wise/" in result.output
        assert "codex-wise init" in result.output

    def test_update_no_state(self, runner, tmp_path):
        """update without prior init should error."""
        (tmp_path / ".codex-wise").mkdir()
        result = runner.invoke(cli, ["update", str(tmp_path)])
        assert result.exit_code != 0
