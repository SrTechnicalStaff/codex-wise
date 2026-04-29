"""Dart and Flutter import resolution."""

from __future__ import annotations

import json
import posixpath
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .context import ResolverContext


def _normalize(path: str) -> str:
    return posixpath.normpath(path.replace("\\", "/")).lstrip("./")


def _with_dart_suffix(path: str) -> list[str]:
    normalized = _normalize(path)
    candidates = [normalized]
    if not normalized.endswith(".dart"):
        candidates.append(f"{normalized}.dart")
    return candidates


@lru_cache(maxsize=64)
def _load_package_index(repo_path_str: str) -> dict[str, str]:
    """Return package name to repo-relative lib root."""
    repo_path = Path(repo_path_str)
    packages: dict[str, str] = {}

    package_config = repo_path / ".dart_tool" / "package_config.json"
    if package_config.exists():
        try:
            data = json.loads(package_config.read_text(encoding="utf-8"))
            for package in data.get("packages", []):
                name = package.get("name")
                root_uri = package.get("rootUri")
                package_uri = package.get("packageUri", "lib/")
                if not name or not root_uri:
                    continue
                root_abs = (package_config.parent / root_uri).resolve()
                lib_abs = (root_abs / package_uri).resolve()
                try:
                    packages[name] = lib_abs.relative_to(repo_path).as_posix()
                except ValueError:
                    continue
        except Exception:
            pass

    for pubspec in repo_path.rglob("pubspec.yaml"):
        if any(part in {".dart_tool", "build"} for part in pubspec.parts):
            continue
        try:
            data: Any = yaml.safe_load(pubspec.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        name = data.get("name")
        if not isinstance(name, str) or not name:
            continue
        lib_dir = pubspec.parent / "lib"
        if lib_dir.exists():
            try:
                packages.setdefault(name, lib_dir.relative_to(repo_path).as_posix())
            except ValueError:
                pass

    return packages


def _package_index(ctx: ResolverContext) -> dict[str, str]:
    if not ctx.repo_path:
        return {}
    return _load_package_index(str(ctx.repo_path.resolve()))


def _first_existing(candidates: list[str], ctx: ResolverContext) -> str | None:
    for candidate in candidates:
        if candidate in ctx.path_set:
            return candidate
    return None


def resolve_dart_import(
    module_path: str,
    importer_path: str,
    ctx: ResolverContext,
) -> str | None:
    """Resolve Dart relative, package:, and same-package imports."""
    module_path = module_path.strip().strip("\"'")
    if not module_path:
        return None
    if module_path.startswith("dart:"):
        return None

    candidates: list[str] = []

    if module_path.startswith("package:"):
        package_tail = module_path.split(":", 1)[1]
        package_name, _, rest = package_tail.partition("/")
        lib_root = _package_index(ctx).get(package_name)
        if lib_root and rest:
            candidates.extend(_with_dart_suffix(f"{lib_root}/{rest}"))
        if rest:
            candidates.extend(_with_dart_suffix(f"lib/{rest}"))
        candidates.extend(_with_dart_suffix(package_tail))
    elif module_path.startswith("."):
        base = PurePosixPath(importer_path).parent
        candidates.extend(_with_dart_suffix((base / module_path).as_posix()))
    else:
        importer_parts = PurePosixPath(importer_path).parts
        if importer_parts and importer_parts[0] == "lib":
            candidates.extend(_with_dart_suffix(f"lib/{module_path}"))
        candidates.extend(_with_dart_suffix(module_path))

    resolved = _first_existing(candidates, ctx)
    if resolved:
        return resolved

    return None
