"""Dart heritage extraction."""

from __future__ import annotations

from tree_sitter import Node

from ...models import HeritageRelation
from ..helpers import node_text


def _extract_type_names(node: Node, src: str) -> list[str]:
    names: list[str] = []

    def walk(current: Node) -> None:
        if current.type == "type_identifier":
            name = node_text(current, src).strip()
            if name:
                names.append(name)
            return
        for child in current.children:
            walk(child)

    walk(node)
    return names


def _append(
    out: list[HeritageRelation],
    *,
    child_name: str,
    parent_name: str,
    kind: str,
    line: int,
) -> None:
    if parent_name == child_name:
        return
    out.append(
        HeritageRelation(
            child_name=child_name,
            parent_name=parent_name,
            kind=kind,  # type: ignore[arg-type]
            line=line,
        )
    )


def _extract_dart_heritage(
    def_node: Node,
    name: str,
    line: int,
    src: str,
    out: list[HeritageRelation],
) -> None:
    """Extract class Foo extends Bar implements Baz with Mixin."""
    for child in def_node.children:
        if child.type == "superclass":
            for parent in _extract_type_names(child, src):
                _append(out, child_name=name, parent_name=parent, kind="extends", line=line)
        elif child.type == "interfaces":
            for parent in _extract_type_names(child, src):
                _append(out, child_name=name, parent_name=parent, kind="implements", line=line)
        elif child.type in {"mixin_application", "on_clause", "mixins"}:
            for parent in _extract_type_names(child, src):
                _append(out, child_name=name, parent_name=parent, kind="mixin", line=line)
