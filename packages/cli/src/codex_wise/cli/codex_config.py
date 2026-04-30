"""Project-scoped Codex configuration helpers."""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

import click

_CODEX_WISE_TABLE = "mcp_servers.codex_wise"
_LEGACY_TABLES = ("mcp_servers.codex-wise",)
_CODEX_WISE_COMMAND = "codex-wise"
_STARTUP_TIMEOUT_SEC = 20
_TOOL_TIMEOUT_SEC = 120


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _normalize_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def resolve_codex_wise_command(
    command_resolver: Callable[[str], str | None] = shutil.which,
) -> str:
    """Return a Desktop-friendly command path for the codex-wise executable."""
    resolved = command_resolver(_CODEX_WISE_COMMAND)
    if resolved:
        return _normalize_path(Path(resolved))
    return _CODEX_WISE_COMMAND


def generate_codex_mcp_table(
    repo_path: Path,
    *,
    command_resolver: Callable[[str], str | None] = shutil.which,
) -> str:
    """Return the TOML table for the codex-wise mcp server."""
    abs_path = _normalize_path(repo_path)
    args = ["mcp", abs_path, "--transport", "stdio"]
    command = resolve_codex_wise_command(command_resolver)
    return "\n".join(
        [
            f"[{_CODEX_WISE_TABLE}]",
            f"command = {_toml_string(command)}",
            f"args = {json.dumps(args)}",
            f"cwd = {_toml_string(abs_path)}",
            (
                'env = { CODEX_WISE_PROVIDER = "codex_app", '
                'CODEX_WISE_CODEX_TRANSPORT = "proxy", '
                'CODEX_WISE_DOC_MODEL = "gpt-5.5", '
                'CODEX_WISE_CODEX_REASONING_EFFORT = "medium" }'
            ),
            f"startup_timeout_sec = {_STARTUP_TIMEOUT_SEC}",
            f"tool_timeout_sec = {_TOOL_TIMEOUT_SEC}",
        ]
    )


def save_project_codex_config(
    repo_path: Path,
    *,
    command_resolver: Callable[[str], str | None] = shutil.which,
) -> Path:
    """Merge the codex-wise mcp server into <repo>/.codex/config.toml."""
    codex_dir = repo_path / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    config_path = codex_dir / "config.toml"
    table = generate_codex_mcp_table(repo_path, command_resolver=command_resolver)

    if config_path.exists():
        content = _load_valid_toml_text(config_path)
        merged = _replace_or_append_table(content, (_CODEX_WISE_TABLE, *_LEGACY_TABLES), table)
    else:
        merged = table + "\n"

    config_path.write_text(merged, encoding="utf-8")
    return config_path


def _load_valid_toml_text(config_path: Path) -> str:
    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(
            f"Cannot update {config_path}: existing file could not be read. "
            "Fix the file permissions and retry; no changes were written."
        ) from exc

    try:
        tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise click.ClickException(
            f"Cannot update {config_path}: existing file is not valid TOML. "
            "Fix or remove it and retry; no changes were written."
        ) from exc
    return content


def _replace_or_append_table(content: str, table_names: tuple[str, ...], replacement: str) -> str:
    lines = content.splitlines()
    table_res = [
        re.compile(rf"^\s*\[{re.escape(table_name)}\]\s*(?:#.*)?$")
        for table_name in table_names
    ]
    any_table_re = re.compile(r"^\s*\[+[^]]+\]+\s*(?:#.*)?$")

    ranges: list[tuple[int, int]] = []
    for idx, line in enumerate(lines):
        if any(table_re.match(line) for table_re in table_res):
            end = len(lines)
            for next_idx in range(idx + 1, len(lines)):
                if any_table_re.match(lines[next_idx]):
                    end = next_idx
                    break
            ranges.append((idx, end))

    if not ranges:
        prefix = content.rstrip()
        if not prefix:
            return replacement + "\n"
        return prefix + "\n\n" + replacement + "\n"

    first_start = ranges[0][0]
    replacement_lines = replacement.splitlines()
    merged: list[str] = []
    inserted = False
    idx = 0
    for start, end in ranges:
        merged.extend(lines[idx:start])
        if not inserted:
            merged.extend(replacement_lines)
            inserted = True
        idx = end
    merged.extend(lines[idx:])
    if not inserted:
        merged = lines[:first_start] + replacement_lines + lines[first_start:]
    return "\n".join(merged).rstrip() + "\n"
