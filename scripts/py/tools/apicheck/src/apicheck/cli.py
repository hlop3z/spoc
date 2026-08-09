"""Thin CLI adapter over `apicheck.core` (Rule 2 — no logic lives here)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from apicheck import extract, packaging
from apicheck.core import (
    Contract,
    Finding,
    Observation,
    derive_contract,
    diff,
    exit_code,
    merge,
)
from apicheck.manifest import ManifestError, load_contract

app = cyclopts.App(
    name="apicheck",
    help="Check spoc's declared stability contract against its real surface.",
)


def _observe(repo: Path) -> tuple[Observation, Contract, list[Finding]]:
    """The full contract and surface: rules for imports, declaration for the rest.

    The two halves never overlap — `manifest` refuses an importable name and the
    derivation only ever sees one — so the merge cannot produce a conflict, and
    `Contract.overlaps()` still checks that rather than assuming it.
    """
    declared = load_contract(repo / "pyproject.toml")
    derived, unresolved = derive_contract(extract.exposures(repo / "src"))

    return (
        Observation(
            elements=frozenset(derived.declared | packaging.observe(repo)),
            verified_kinds=frozenset({extract.VERIFIED_KIND})
            | packaging.VERIFIED_KINDS,
        ),
        merge(derived, declared),
        unresolved,
    )


@app.default
def main(
    repo: Annotated[
        Path,
        cyclopts.Parameter(help="Repository root. Defaults to the current directory."),
    ] = Path("."),
    *,
    as_json: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--json"], help="Emit JSON instead of a readable list."
        ),
    ] = False,
) -> int:
    """Report every divergence between `[tool.spoc.stability]` and the real surface.

    Exits non-zero on any fatal finding, so it can gate a check run.
    """
    repo = repo.resolve()
    try:
        observed, contract, unresolved = _observe(repo)
    except ManifestError as exc:
        print(f"apicheck: {exc}", file=sys.stderr)
        return 2

    findings = sorted(unresolved + diff(contract, observed))

    if as_json:
        json.dump(
            [
                {"kind": f.kind.value, "element": f.element, "detail": f.detail}
                for f in findings
            ],
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    elif findings:
        for finding in findings:
            print(finding)
        fatal = sum(1 for f in findings if f.fatal)
        skipped = len(findings) - fatal
        summary = f"\n{fatal} fatal finding(s)"
        if skipped:
            summary += f", {skipped} unverifiable (reported, not fatal)"
        print(summary, file=sys.stderr)
    else:
        print(f"surface matches the contract ({len(contract.declared)} elements)")

    return exit_code(findings)


if __name__ == "__main__":
    sys.exit(app())
