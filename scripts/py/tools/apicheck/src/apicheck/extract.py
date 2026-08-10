"""Adapter: the importable surface, extracted with griffe.

Static analysis — the package is never imported, so the check runs against the
working tree and needs no installed distribution (nor a released one).

Griffe covers importable names only; it documents that it cannot see console
scripts, entry points, or extras. Those come from `packaging.py`, and both feed
the same core.
"""

from __future__ import annotations

import ast
import functools
import re
from pathlib import Path
from typing import NamedTuple

import griffe

from apicheck.core import (
    PROVISIONAL_NOTICE,
    PYTHON,
    Exposure,
    Finding,
    Kind,
    Withdrawal,
    states_replacement,
    states_settling_condition,
)

# `NAME = value` / `NAME: T = value` at module level.
_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=")

# The single import site for the deprecation signal, per the PEP 702 decision in
# DECISIONS.md. A withdrawal signal produced anywhere else is unsanctioned: the
# absence of a mark can only mean "not being withdrawn" if there is exactly one
# way to write one.
SANCTIONED_MARK_MODULE = "spoc.core.deprecation"

# How that module's two spellings appear in the source. `deprecated_alias`
# withdraws a re-exported *name*; `@deprecated` withdraws a definition.
_ALIAS_MARK = "deprecated_alias"
_DECORATOR_MARK = "deprecated"


class _Module(NamedTuple):
    """One source file, named the way an importer would name it."""

    dotted: str
    path: Path
    source: str


def _modules(source_root: Path, package: str) -> list[_Module]:
    """Every source file of the package, with its dotted module path."""
    found = []
    for path in sorted((source_root / package).rglob("*.py")):
        parts = path.relative_to(source_root).with_suffix("").parts
        dotted = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        found.append(_Module(dotted, path, path.read_text(encoding="utf-8")))
    return found


@functools.cache
def _parsed(source_root: Path, package: str) -> tuple[tuple[_Module, ast.Module], ...]:
    """Every module that parses, with its syntax tree.

    Cached because two readers want it — the mark reader and the unsanctioned
    signal scan — and parsing the tree twice to answer two questions about the
    same bytes would be waste, not independence.

    A file that does not parse is skipped rather than raised on; `_parse_gaps`
    is what reports it. The gate must not crash on code it merely failed to
    read, and must not quietly call that code mark-free either.
    """
    trees = []
    for module in _modules(source_root, package):
        try:
            trees.append((module, ast.parse(module.source, filename=str(module.path))))
        except SyntaxError:
            continue
    return tuple(trees)


def _parse_gaps(source_root: Path, package: str) -> list[Finding]:
    """A file whose withdrawal state could not be read, reported as a gap."""
    parsed = {module.dotted for module, _ in _parsed(source_root, package)}
    return [
        Finding(
            Kind.UNVERIFIABLE,
            module.dotted,
            "could not be parsed, so its withdrawal marks were not read",
        )
        for module in _modules(source_root, package)
        if module.dotted not in parsed
    ]


def _string_argument(node: ast.expr | None) -> str | None:
    """A call argument as its literal string, or `None` if it is not one.

    Implicit concatenation across lines needs no handling here: the parser folds
    adjacent literals into one constant before this ever sees them, which is
    precisely why the mark is read from a syntax tree rather than a pattern.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _called_name(node: ast.expr) -> str:
    """The trailing name of whatever is being called or applied."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _assigned_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    """The plain names an assignment binds, ignoring anything more elaborate."""
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    return [node.target.id] if isinstance(node.target, ast.Name) else []


def _alias_mark(dotted: str, node: ast.Assign | ast.AnnAssign) -> dict[str, str]:
    """`NAME = deprecated_alias(target, message)` — a withdrawn re-export.

    Withdraws the *name*, leaving the definition it forwards to unmarked, which
    is the whole reason that helper exists.
    """
    call = node.value
    if not isinstance(call, ast.Call) or _called_name(call.func) != _ALIAS_MARK:
        return {}
    if len(call.args) < 2:
        return {}

    message = _string_argument(call.args[1])
    if message is None:
        return {}
    return {f"{dotted}.{name}": message for name in _assigned_names(node)}


def _decorator_mark(
    dotted: str, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
) -> dict[str, str]:
    """`@deprecated(message)` — a withdrawn definition, and every path to it."""
    for decorator in node.decorator_list:
        if (
            isinstance(decorator, ast.Call)
            and _called_name(decorator.func) == _DECORATOR_MARK
            and decorator.args
        ):
            message = _string_argument(decorator.args[0])
            if message is not None:
                return {f"{dotted}.{node.name}": message}
    return {}


def _marks(source_root: Path, package: str) -> dict[str, str]:
    """Every marked element mapped to its notice, keyed by dotted path.

    Two spellings, because withdrawal has two subjects: a re-exported name, and
    the definition itself.
    """
    marks: dict[str, str] = {}

    for module, tree in _parsed(source_root, package):
        for node in tree.body:
            if isinstance(node, ast.Assign | ast.AnnAssign):
                marks.update(_alias_mark(module.dotted, node))
            elif isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            ):
                marks.update(_decorator_mark(module.dotted, node))

    return marks


def unsanctioned_marks(source_root: Path, package: str = "spoc") -> list[Finding]:
    """Withdrawal signals raised outside the one module allowed to raise them.

    Scans the whole package rather than only the modules that contribute an
    exposed element. A `DeprecationWarning` raised from an internal module still
    reaches a consumer at runtime, and the failure being prevented — a mark the
    observer does not recognize, reported as no mark at all — does not respect
    the boundary of the published surface.
    """
    findings = _parse_gaps(source_root, package)

    for module, tree in _parsed(source_root, package):
        if module.dotted == SANCTIONED_MARK_MODULE:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _called_name(node.func) != "warn":
                continue
            arguments = list(node.args) + [kw.value for kw in node.keywords]
            if any(
                _called_name(argument) == "DeprecationWarning" for argument in arguments
            ):
                findings.append(
                    Finding(
                        Kind.UNSANCTIONED,
                        f"{module.dotted}:{node.lineno}",
                        "raises a deprecation signal directly - withdrawal is "
                        f"expressed through {SANCTIONED_MARK_MODULE} and nowhere "
                        "else, or an unrecognized mark reads as no mark",
                    )
                )

    return sorted(findings)


def _comment_docs(source_root: Path, package: str) -> dict[str, str]:
    """Attribute docs written as a `#:` comment block, keyed by dotted path.

    Griffe reads docstrings, not `#:` comments, and this codebase documents every
    module constant with the latter. Without this the extractor would call a
    fully documented constant undocumented — a defect in the observer, not in the
    code it observes.
    """
    docs: dict[str, str] = {}

    for module in _modules(source_root, package):
        dotted = module.dotted

        buffer: list[str] = []
        for line in module.source.splitlines():
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


def _mark_of(member, exposed: str, marks: dict[str, str]) -> str | None:
    """The notice withdrawing this element, by its own path or its target's.

    Both are consulted because the two spellings withdraw different things. A
    withdrawn re-export is marked at the path it is exposed under; a withdrawn
    definition is marked where it is defined, and every name reaching it is
    withdrawn with it.
    """
    if exposed in marks:
        return marks[exposed]
    if member is not None and getattr(member, "is_alias", False):
        try:
            return marks.get(str(member.target_path))
        except Exception:
            return None
    return None


def _walk(
    module,
    path: str,
    elements: dict[str, tuple[str, bool | None, str | None]],
    comments: dict,
    marks: dict[str, str],
) -> None:
    """Collect `path.name -> (documentation, from-a-package, notice)` recursively."""
    from_package = _is_package(module)

    for name in _exported_names(module):
        member = (module.members or {}).get(name)
        exposed = f"{path}.{name}"
        elements[exposed] = (
            _docstring(member, comments) if member is not None else "",
            from_package,
            _mark_of(member, exposed, marks),
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
        _walk(member, f"{path}.{name}", elements, comments, marks)


def _observe(
    source_root: Path, package: str
) -> dict[str, tuple[str, bool | None, str | None]]:
    """Every exported name mapped to its documentation, module, and notice."""
    module = griffe.load(package, search_paths=[str(source_root)])
    comments = _comment_docs(source_root, package)
    marks = _marks(source_root, package)

    elements: dict[str, tuple[str, bool | None, str | None]] = {}
    _walk(module, package, elements, comments, marks)
    return elements


def exposures(source_root: Path, package: str = "spoc") -> list[Exposure]:
    """The facts the tier rules run on, one per exposed importable name."""
    return [
        Exposure(
            element=name,
            from_package=from_package,
            documented=PROVISIONAL_NOTICE.lower() in doc.lower(),
            settling_stated=states_settling_condition(doc),
            withdrawal=(
                None
                if notice is None
                else Withdrawal(
                    message=notice,
                    replacement_stated=states_replacement(notice, name),
                )
            ),
        )
        for name, (doc, from_package, notice) in _observe(source_root, package).items()
    ]


VERIFIED_KIND = PYTHON
