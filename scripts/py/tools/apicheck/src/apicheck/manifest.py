"""Adapter: read the declared contract out of `[tool.spoc.stability]`.

Uses stdlib `tomllib` and reads the file directly rather than importing the
package it is auditing — a checker that imports its subject would be verifying
whatever happens to be installed, not what the working tree declares.

The table declares only what no static observer can attribute a tier to: the
console script, the plugin entry point, the extras, the fixtures, the config
schema, the template set. Importable names are not declared here — their tier
follows from the source, via `core.derive_tier`. A dotted name appearing in this
table is therefore a mistake, and is refused rather than merged.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from apicheck.core import PYTHON, Contract, kind_of


class ManifestError(RuntimeError):
    """The manifest is missing or malformed."""


def _tier(table: dict, name: str, source: Path) -> frozenset[str]:
    complaint = f"{source}: [tool.spoc.stability].{name} must be a list of strings"

    values = table.get(name, [])
    if not isinstance(values, list):
        raise ManifestError(complaint)

    elements: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ManifestError(complaint)
        if kind_of(value) == PYTHON:
            raise ManifestError(
                f"{source}: [tool.spoc.stability].{name} declares the importable "
                f"name {value!r}. Importable tiers are derived from the source, "
                f"not declared — expose it differently to change its tier."
            )
        elements.add(value)
    return frozenset(elements)


def load_contract(pyproject: Path) -> Contract:
    """Parse the stability table. Raises `ManifestError` if it is absent."""
    if not pyproject.is_file():
        raise ManifestError(f"{pyproject}: no such file")

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    table = data.get("tool", {}).get("spoc", {}).get("stability")
    if table is None:
        raise ManifestError(f"{pyproject}: no [tool.spoc.stability] table")

    return Contract(
        public=_tier(table, "public", pyproject),
        provisional=_tier(table, "provisional", pyproject),
        internal=_tier(table, "internal", pyproject),
    )
