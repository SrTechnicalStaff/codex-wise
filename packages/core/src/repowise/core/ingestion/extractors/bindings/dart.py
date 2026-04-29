"""Dart import-binding extraction."""

from __future__ import annotations

import re

from tree_sitter import Node

from ...models import NamedBinding
from ..helpers import node_text

_ALIAS_RE = re.compile(r"\bas\s+([A-Za-z_]\w*)")
_SHOW_RE = re.compile(r"\bshow\s+([^;]+)")
_HIDE_RE = re.compile(r"\bhide\s+([^;]+)")


def _split_names(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def extract_dart_bindings(stmt_node: Node, src: str) -> tuple[list[str], list[NamedBinding]]:
    """Extract aliases and explicit combinators from a Dart import."""
    raw = node_text(stmt_node, src)
    names: list[str] = []
    bindings: list[NamedBinding] = []

    alias_match = _ALIAS_RE.search(raw)
    if alias_match:
        alias = alias_match.group(1)
        names.append(alias)
        bindings.append(
            NamedBinding(
                local_name=alias,
                exported_name=None,
                source_file=None,
                is_module_alias=True,
            )
        )

    show_match = _SHOW_RE.search(raw)
    if show_match:
        for name in _split_names(show_match.group(1)):
            names.append(name)
            bindings.append(NamedBinding(local_name=name, exported_name=name, source_file=None))

    # A hide combinator still imports the rest of the library. Preserve the
    # hidden names as metadata-like imported_names so downstream display is honest.
    hide_match = _HIDE_RE.search(raw)
    if hide_match and not names:
        names.extend(f"!{name}" for name in _split_names(hide_match.group(1)))

    return names, bindings
