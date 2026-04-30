"""Dart import-binding extraction."""

from __future__ import annotations

import re

from tree_sitter import Node

from ...models import NamedBinding
from ..helpers import node_text

_ALIAS_RE = re.compile(r"\bas\s+([A-Za-z_]\w*)")
_SHOW_RE = re.compile(r"\bshow\s+([^;]+)")


def extract_dart_bindings(stmt_node: Node, src: str) -> tuple[list[str], list[NamedBinding]]:
    """Extract aliases and explicit `show` imports from a Dart import."""
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
        for part in show_match.group(1).split(","):
            name = part.strip()
            if not name:
                continue
            names.append(name)
            bindings.append(
                NamedBinding(local_name=name, exported_name=name, source_file=None)
            )

    return names, bindings
