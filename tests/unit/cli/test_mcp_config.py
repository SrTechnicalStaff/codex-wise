import json
import re
from pathlib import Path

import click
import pytest

from codex_wise.cli import mcp_config


def _codex_wise_entry(repo_path: Path) -> dict:
    return mcp_config.generate_mcp_config(repo_path)["mcpServers"]


def test_save_mcp_config_uses_native_storage(tmp_path: Path) -> None:
    config_path = mcp_config.save_mcp_config(tmp_path)

    assert config_path == tmp_path / ".codex-wise" / "mcp.json"
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["mcpServers"]["codex_wise"]["command"] == "codex-wise"


def test_merge_mcp_entry_creates_missing_file(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"

    assert mcp_config._merge_mcp_entry(config_path, _codex_wise_entry(tmp_path))

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert "codex_wise" in saved["mcpServers"]


def test_merge_mcp_entry_merges_valid_existing_file(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {"existing": {"command": "existing"}},
                "permissions": {"allow": ["Bash(git status:*)"]},
            }
        ),
        encoding="utf-8",
    )

    assert mcp_config._merge_mcp_entry(config_path, _codex_wise_entry(tmp_path))

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["mcpServers"]["existing"] == {"command": "existing"}
    assert "codex_wise" in saved["mcpServers"]
    assert saved["permissions"] == {"allow": ["Bash(git status:*)"]}


def test_merge_mcp_entry_rejects_invalid_existing_file(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    original = '{\n  "permissions": {},\n}\n'
    config_path.write_text(original, encoding="utf-8")

    with pytest.raises(click.ClickException, match=re.escape(str(config_path))):
        mcp_config._merge_mcp_entry(config_path, _codex_wise_entry(tmp_path))

    assert config_path.read_text(encoding="utf-8") == original
