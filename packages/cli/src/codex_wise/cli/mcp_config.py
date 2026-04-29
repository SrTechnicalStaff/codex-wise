"""Auto-generated MCP config for MCP clients."""

from __future__ import annotations

import json
from pathlib import Path

import click

from codex_wise.core.persistence.database import ensure_repo_storage_dir, get_repo_storage_dir


def generate_mcp_config(repo_path: Path) -> dict:
    """Generate MCP config JSON for a repository.

    Returns a dict in the standard mcpServers format.
    """
    abs_path = str(repo_path.resolve()).replace("\\", "/")
    return {
        "mcpServers": {
            "codex_wise": {
                "command": "codex-wise",
                "args": ["mcp", abs_path, "--transport", "stdio"],
                "description": "Codex Wise: codebase context, graph, git signals, dead code, and decisions",
            }
        }
    }


def save_mcp_config(repo_path: Path) -> Path:
    """Save MCP config to native repo storage and return the path."""
    storage_dir = ensure_repo_storage_dir(repo_path)
    config_path = storage_dir / "mcp.json"
    config = generate_mcp_config(repo_path)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config_path


def _merge_mcp_entry(config_path: Path, new_entry: dict) -> bool:
    """Merge *new_entry* into the mcpServers block of *config_path*.

    Creates the file if it doesn't exist. Returns True on success.
    """
    try:
        if config_path.exists():
            existing = _load_existing_config(config_path)
        else:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            existing = {}

        servers = dict(existing.get("mcpServers", {}))
        servers.update(new_entry)
        existing["mcpServers"] = servers
        config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def _load_existing_config(config_path: Path) -> dict:
    """Load an existing JSON config without silently replacing bad content."""
    try:
        existing = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(
            f"Cannot update {config_path}: existing file is not valid JSON. "
            "Fix or remove it and retry; no changes were written."
        ) from exc
    except OSError as exc:
        raise click.ClickException(
            f"Cannot update {config_path}: existing file could not be read. "
            "Fix the file permissions and retry; no changes were written."
        ) from exc
    if not isinstance(existing, dict):
        raise click.ClickException(
            f"Cannot update {config_path}: existing file must contain a JSON object. "
            "Fix or remove it and retry; no changes were written."
        )
    return existing


def format_setup_instructions(repo_path: Path) -> str:
    """Return human-readable setup instructions for MCP clients."""
    config = generate_mcp_config(repo_path)
    server_block = json.dumps(config["mcpServers"]["codex_wise"], indent=4)
    abs_path = str(repo_path.resolve()).replace("\\", "/")

    return f"""
Codex Wise MCP Server Configuration
===================================

Codex Desktop:
  codex-wise init writes project-local .codex/config.toml automatically.

JSON MCP clients:
  {server_block}

Or run directly:
  codex-wise mcp {abs_path}
  codex-wise mcp {abs_path} --transport sse --port 7338

Config saved to: {get_repo_storage_dir(repo_path) / "mcp.json"}
""".strip()
