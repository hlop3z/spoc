"""Adapter: the surface griffe cannot see.

Griffe covers importable names. A console script, a plugin entry point, an extra,
a pytest fixture and a template set are each things a consumer depends on just as
hard, and none of them is an import. This module observes those, and states which
kinds it covers so the core can tell a missing element from an unwatched one.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

# Kinds this adapter is authoritative for. A declared element whose kind appears
# in neither this set nor griffe's is reported `unverifiable` rather than passed.
VERIFIED_KINDS = frozenset(
    {"script", "entry-point", "extra", "fixture", "template-set"}
)


def _fixtures(plugin: Path) -> set[str]:
    """Pytest fixtures defined in the plugin module, found by AST — never imported."""
    if not plugin.is_file():
        return set()

    tree = ast.parse(plugin.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for deco in node.decorator_list:
            # Matches both `@pytest.fixture` and `@pytest.fixture(...)`.
            target = deco.func if isinstance(deco, ast.Call) else deco
            if (isinstance(target, ast.Attribute) and target.attr == "fixture") or (
                isinstance(target, ast.Name) and target.id == "fixture"
            ):
                found.add(f"fixture:{node.name}")
    return found


def observe(repo_root: Path) -> set[str]:
    """Every non-importable surface element the distribution exposes."""
    pyproject = repo_root / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})

    elements: set[str] = set()

    elements |= {f"script:{name}" for name in project.get("scripts", {})}

    for group, entries in (project.get("entry-points", {}) or {}).items():
        elements |= {f"entry-point:{group}.{name}" for name in entries}

    elements |= {f"extra:{name}" for name in project.get("optional-dependencies", {})}

    elements |= _fixtures(repo_root / "src" / "spoc" / "testing" / "plugin.py")

    templates = repo_root / "src" / "spoc" / "scaffold" / "templates"
    if templates.is_dir():
        elements |= {
            f"template-set:{d.name}" for d in sorted(templates.iterdir()) if d.is_dir()
        }

    return elements
