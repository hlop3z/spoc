"""Adapter: the importable surface, extracted with griffe.

Static analysis — the package is never imported, so the check runs against the
working tree and needs no installed distribution (nor a released one).

Griffe covers importable names only; it documents that it cannot see console
scripts, entry points, or extras. Those come from `packaging.py`, and both feed
the same core.
"""

from __future__ import annotations

import re
from pathlib import Path

import griffe

from apicheck.core import PROVISIONAL_NOTICE, PYTHON, Exposure

# `NAME = value` / `NAME: T = value` at module level.
_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=")


def _comment_docs(source_root: Path, package: str) -> dict[str, str]:
    """Attribute docs written as a `#:` comment block, keyed by dotted path.

    Griffe reads docstrings, not `#:` comments, and this codebase documents every
    module constant with the latter. Without this the extractor would call a
    fully documented constant undocumented — a defect in the observer, not in the
    code it observes.
    """
    docs: dict[str, str] = {}

    for path in sorted((source_root / package).rglob("*.py")):
        parts = path.relative_to(source_root).with_suffix("").parts
        dotted = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)

        buffer: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#:"):
                buffer.append(stripped[2:].strip())
                continue
            if buffer:
                match = _ASSIGN.match(line)
                if match:
                    docs[f"{dotted}.{match.group(1)}"] = "\n".join(buffer)
                buffer = []

    return docs


def _exported_names(module) -> list[str]:
    """The module's `__all__`, normalized to plain strings."""
    exports = getattr(module, "exports", None) or []
    names = []
    for entry in exports:
        name = entry if isinstance(entry, str) else getattr(entry, "name", None)
        if isinstance(name, str):
            names.append(name)
    return names


def _docstring(member, comments: dict[str, str]) -> str:
    """The member's documentation, following an alias to whatever it re-exports.

    Falls back to the `#:` comment block for the resolved path, so a constant is
    judged on the documentation it actually carries.
    """
    target = member
    for _ in range(10):  # alias chains are short; the bound just refuses a cycle
        doc = getattr(target, "docstring", None)
        if doc is not None and getattr(doc, "value", None):
            return str(doc.value)

        by_path = comments.get(str(getattr(target, "path", "")))
        if by_path:
            return by_path

        if not getattr(target, "is_alias", False):
            return ""
        try:
            comment = comments.get(str(target.target_path))
            if comment:
                return comment
            target = target.target
        except Exception:
            return ""
    return ""


def _is_package(module) -> bool | None:
    """Whether this module is a package, or `None` when it cannot be told.

    The distinction carries the `internal` rule, so an unknown answer must stay
    unknown: guessing `False` would quietly demote a public element to internal
    and the check would pass while promising nothing.
    """
    try:
        return bool(module.is_package or module.is_subpackage)
    except Exception:
        return None


def _walk(
    module, path: str, elements: dict[str, tuple[str, bool | None]], comments: dict
) -> None:
    """Collect `path.name -> (documentation, from-a-package)` recursively."""
    from_package = _is_package(module)

    for name in _exported_names(module):
        member = (module.members or {}).get(name)
        elements[f"{path}.{name}"] = (
            _docstring(member, comments) if member is not None else "",
            from_package,
        )

    for name, member in sorted((module.members or {}).items()):
        # `is_alias` first: reading `.kind` on an alias forces resolution, and an
        # alias that cannot resolve — a conditional stdlib import, say — raises
        # rather than returning the getattr default. The gate must not crash on
        # code it merely failed to follow.
        if name.startswith("_") or getattr(member, "is_alias", False):
            continue
        try:
            is_module = member.kind == griffe.Kind.MODULE
        except Exception:
            continue
        if not is_module:
            continue
        _walk(member, f"{path}.{name}", elements, comments)


def _observe(source_root: Path, package: str) -> dict[str, tuple[str, bool | None]]:
    """Every exported name mapped to its documentation and its exposing module."""
    module = griffe.load(package, search_paths=[str(source_root)])
    comments = _comment_docs(source_root, package)

    elements: dict[str, tuple[str, bool | None]] = {}
    _walk(module, package, elements, comments)
    return elements


def exposures(source_root: Path, package: str = "spoc") -> list[Exposure]:
    """The facts the tier rules run on, one per exposed importable name."""
    return [
        Exposure(
            element=name,
            from_package=from_package,
            documented=PROVISIONAL_NOTICE.lower() in doc.lower(),
        )
        for name, (doc, from_package) in _observe(source_root, package).items()
    ]


VERIFIED_KIND = PYTHON
