"""Dart import resolution."""

from __future__ import annotations

from pathlib import PurePosixPath

from .context import ResolverContext


def _with_dart_suffix(path: str) -> list[str]:
    candidates = [path]
    if not path.endswith(".dart"):
        candidates.append(f"{path}.dart")
    return candidates


def resolve_dart_import(
    module_path: str,
    importer_path: str,
    ctx: ResolverContext,
) -> str | None:
    """Resolve Dart relative and same-package imports into repo-relative paths."""
    module_path = module_path.strip().strip("\"'")
    if not module_path or module_path.startswith("dart:"):
        return None

    candidates: list[str] = []

    if module_path.startswith("package:"):
        package_tail = module_path.split(":", 1)[1]
        parts = package_tail.split("/", 1)
        if len(parts) == 2:
            candidates.extend(_with_dart_suffix(f"lib/{parts[1]}"))
        candidates.extend(_with_dart_suffix(package_tail))
    elif module_path.startswith("."):
        base = PurePosixPath(importer_path).parent
        resolved = (base / module_path).as_posix()
        candidates.extend(_with_dart_suffix(resolved))
    else:
        candidates.extend(_with_dart_suffix(module_path))

    for candidate in candidates:
        if candidate in ctx.path_set:
            return candidate

    return ctx.stem_lookup(PurePosixPath(module_path).stem.lower())
