"""Git hook management for Codex Wise auto-sync.

Installs/uninstalls a post-commit hook that runs ``codex-wise update`` in the
background after every commit, keeping the wiki in sync automatically.

The hook uses start/end markers so it can safely coexist with other hooks
in the same file (e.g. lint hooks, graphify hooks).
"""

from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path

_HOOK_MARKER = "# Codex Wise-hook-start"
_HOOK_MARKER_END = "# Codex Wise-hook-end"

# The hook script detects the platform and runs codex-wise update in the
# background so the commit is never blocked.
_HOOK_SCRIPT = """\
# Codex Wise-hook-start
# Auto-syncs Codex Wise after each commit (background, non-blocking).
# Installed by: codex-wise hook install
(
  cd "$(git rev-parse --show-toplevel)" || exit 1
  if [ -d ".codex-wise" ]; then
    # Detect the right way to invoke codex-wise
    if command -v codex-wise >/dev/null 2>&1; then
      codex-wise update > /dev/null 2>&1
    elif command -v uv >/dev/null 2>&1; then
      uv run codex-wise update > /dev/null 2>&1
    elif command -v powershell.exe >/dev/null 2>&1; then
      powershell.exe -Command "uv run codex-wise update" > /dev/null 2>&1
    fi
  fi
) &
# Codex Wise-hook-end
"""


def _git_root(path: Path) -> Path | None:
    """Walk up to find .git directory."""
    current = path.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def install(repo_path: Path) -> str:
    """Install a Codex Wise post-commit hook in the repo's .git/hooks/.

    Appends to an existing post-commit hook if one exists (preserving
    other tools' hooks). Returns a human-readable status message.
    """
    root = _git_root(repo_path)
    if root is None:
        return "not a git repository"

    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "post-commit"

    if hook_path.exists():
        content = hook_path.read_text(encoding="utf-8")
        if _HOOK_MARKER in content:
            return "already installed"
        # Append to existing hook
        hook_path.write_text(
            content.rstrip() + "\n\n" + _HOOK_SCRIPT,
            encoding="utf-8",
        )
    else:
        hook_path.write_text("#!/bin/sh\n" + _HOOK_SCRIPT, encoding="utf-8")

    # Make executable (no-op on Windows but harmless)
    try:
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass

    return "installed"


def uninstall(repo_path: Path) -> str:
    """Remove the Codex Wise section from the post-commit hook.

    Preserves other tools' hook content. Deletes the file entirely if
    Codex Wise was the only content.
    """
    root = _git_root(repo_path)
    if root is None:
        return "not a git repository"

    hook_path = root / ".git" / "hooks" / "post-commit"
    if not hook_path.exists():
        return "no post-commit hook found"

    content = hook_path.read_text(encoding="utf-8")
    if _HOOK_MARKER not in content:
        return "codex-wise hook not found in post-commit"

    new_content = re.sub(
        rf"{re.escape(_HOOK_MARKER)}.*?{re.escape(_HOOK_MARKER_END)}\n?",
        "",
        content,
        flags=re.DOTALL,
    ).strip()

    if not new_content or new_content in ("#!/bin/bash", "#!/bin/sh"):
        hook_path.unlink()
        return "removed"
    else:
        hook_path.write_text(new_content + "\n", encoding="utf-8")
        return "removed (other hook content preserved)"


def status(repo_path: Path) -> str:
    """Check if the Codex Wise post-commit hook is installed."""
    root = _git_root(repo_path)
    if root is None:
        return "not a git repository"

    hook_path = root / ".git" / "hooks" / "post-commit"
    if not hook_path.exists():
        return "not installed"

    content = hook_path.read_text(encoding="utf-8")
    if _HOOK_MARKER in content:
        return "installed"
    return "not installed"
