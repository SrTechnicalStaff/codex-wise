"""CLI invocation helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import click


def cli_name(default: str = "Codex Wise") -> str:
    """Return the executable name used for the current Click invocation."""
    ctx = click.get_current_context(silent=True)
    if ctx is not None:
        root = ctx.find_root()
        if root.info_name and root.info_name not in {"cli", "python", "pytest", "__main__"}:
            return root.info_name

    stem = Path(sys.argv[0]).stem
    if stem and stem not in {"python", "pytest", "__main__"}:
        return stem
    return default


def command(*parts: object) -> str:
    """Format a command example using the active CLI name."""
    suffix = " ".join(str(part) for part in parts if str(part))
    return f"{cli_name()} {suffix}".strip()
