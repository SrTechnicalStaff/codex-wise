"""Abstract base class for editor-file generators such as AGENTS.md.

Handles the marker-based merge strategy so subclasses only need to define
the filename, marker tag, template name, and user placeholder text.

Merge rules:
  - No existing file      → create with placeholder + managed section
  - File without markers  → append managed section at bottom
  - File with markers     → replace ONLY content between markers
"""

from __future__ import annotations

import re
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import jinja2

from .data import EditorFileData


class BaseEditorFileGenerator(ABC):
    """Base class for generating and maintaining editor configuration files."""

    #: Format strings for the HTML comment markers. {tag} is replaced by marker_tag.
    MARKER_START_FMT = "<!-- {tag}:START — Do not edit below this line. Auto-generated. -->"
    MARKER_END_FMT = "<!-- {tag}:END -->"

    def __init__(self) -> None:
        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        self._jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(templates_dir)),
            undefined=jinja2.StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ------------------------------------------------------------------
    # Abstract interface — subclasses define these
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def filename(self) -> str:
        """Output filename, e.g. 'AGENTS.md'."""

    @property
    @abstractmethod
    def marker_tag(self) -> str:
        """Marker tag prefix, e.g. 'CODEX_WISE'. Used in START/END comments."""

    @property
    @abstractmethod
    def template_name(self) -> str:
        """Jinja2 template file name, e.g. 'agents_md.j2'."""

    @property
    @abstractmethod
    def user_placeholder(self) -> str:
        """Content written above the Codex Wise section when creating a new file."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, data: EditorFileData) -> str:
        """Render just the managed section content (without markers)."""
        template = self._jinja_env.get_template(self.template_name)
        return template.render(data=data)

    def write(self, repo_path: Path, data: EditorFileData) -> Path:
        """Write the file to *repo_path*, preserving user content outside markers.

        Returns the path of the written file.
        """
        target = repo_path / self.filename
        marker_start = self.MARKER_START_FMT.format(tag=self.marker_tag)
        marker_end = self.MARKER_END_FMT.format(tag=self.marker_tag)

        managed = self.render(data)
        wrapped = f"{marker_start}\n{managed}\n{marker_end}"

        if not target.exists():
            content = f"{self.user_placeholder}\n{wrapped}\n"
        else:
            existing = target.read_text(encoding="utf-8")
            match = self._find_marker_pair(existing)
            if match is not None:
                # Replace the managed section in-place.
                existing_start, existing_end = match
                pattern = re.escape(existing_start) + r".*?" + re.escape(existing_end)
                content = re.sub(pattern, wrapped, existing, flags=re.DOTALL)
            else:
                # Append managed section; preserve all existing content
                content = existing.rstrip() + "\n\n" + wrapped + "\n"

        _atomic_write(target, content)
        return target

    def render_full(self, repo_path: Path, data: EditorFileData) -> str:
        """Return what the full file would look like without writing to disk."""
        marker_start = self.MARKER_START_FMT.format(tag=self.marker_tag)
        marker_end = self.MARKER_END_FMT.format(tag=self.marker_tag)
        managed = self.render(data)
        wrapped = f"{marker_start}\n{managed}\n{marker_end}"
        target = repo_path / self.filename
        if not target.exists():
            return f"{self.user_placeholder}\n{wrapped}\n"
        existing = target.read_text(encoding="utf-8")
        match = self._find_marker_pair(existing)
        if match is not None:
            existing_start, existing_end = match
            pattern = re.escape(existing_start) + r".*?" + re.escape(existing_end)
            return re.sub(pattern, wrapped, existing, flags=re.DOTALL)
        return existing.rstrip() + "\n\n" + wrapped + "\n"

    def _find_marker_pair(self, content: str) -> tuple[str, str] | None:
        marker_start = self.MARKER_START_FMT.format(tag=self.marker_tag)
        marker_end = self.MARKER_END_FMT.format(tag=self.marker_tag)
        if marker_start in content and marker_end in content:
            return marker_start, marker_end
        start = re.search(rf"<!--\s*{re.escape(self.marker_tag)}:START.*?-->", content)
        if start and marker_end in content:
            return start.group(0), marker_end
        return None


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via a temp file + rename."""
    parent = path.parent
    fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        Path(tmp).replace(path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
