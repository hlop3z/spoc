"""Thin CLI adapter for the cross-release surface comparison (Rule 2).

Two questions, two answers, one command:

- *What changed?* — computed here from the derived tiers at both refs, so an
  addition is reported at the tier the element actually carries.
- *Was any of it breaking?* — delegated to griffe, which compares signatures
  rather than names. Classifying a breakage is not something to hand-roll.

Its exit code is bound to the maturity in force. Until 1.0 the contract permits
an incompatible change to a `public` element in a minor release, so failing on
one would make this gate contradict the policy it exists to enforce. It reports
from the start and starts failing at 1.0.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import cyclopts
import griffe

from apicheck import extract
from apicheck.core import derive_contract, surface_delta
from apicheck.release import GitError, declared_version, latest_tag, source_at

app = cyclopts.App(
    name="apidiff",
    help="Compare spoc's surface against the previous release.",
)


def _breakages(old_src: Path, new_src: Path, package: str = "spoc") -> list:
    """Incompatible changes between two source trees, classified by griffe.

    `allow_inspection=False` keeps the no-import invariant: griffe falls back to
    importing a module it cannot read statically, and a checker that imports its
    subject is auditing whatever happens to be installed.
    """

    def load(src: Path):
        return griffe.load(package, search_paths=[str(src)], allow_inspection=False)

    return list(griffe.find_breaking_changes(load(old_src), load(new_src)))


def _render(breakage) -> str:
    """One breakage as a plain line.

    Built from the object rather than `explain()`, which embeds ANSI colour and
    the file path — and that path points into the throwaway directory the
    baseline was unpacked into, which means nothing to a reader. ASCII only, for
    the Windows console this project is developed on.
    """
    detail = str(getattr(breakage.kind, "value", breakage.kind))
    return f"breaking: {breakage.obj.canonical_path} - {detail.lower()}"


@app.default
def main(
    repo: Annotated[
        Path,
        cyclopts.Parameter(help="Repository root. Defaults to the current directory."),
    ] = Path("."),
    *,
    against: Annotated[
        str | None,
        cyclopts.Parameter(
            help="Baseline ref. Defaults to the most recent tag.",
        ),
    ] = None,
) -> int:
    """Report every surface change since the baseline, and whether it breaks.

    Exits 2 when the baseline cannot be resolved — never 0, because a comparison
    that did not happen must not read like a comparison that found nothing.
    """
    repo = repo.resolve()

    try:
        baseline = against or latest_tag(repo)
        version = declared_version(repo)
        with source_at(repo, baseline) as old_src:
            before, _ = derive_contract(extract.exposures(old_src))
            breakages = _breakages(old_src, repo / "src")
    except GitError as exc:
        print(f"apidiff: {exc}", file=sys.stderr)
        return 2

    after, unresolved = derive_contract(extract.exposures(repo / "src"))

    # Always say what was compared. A silent baseline is the same trap as
    # reporting "nobody looked" as "it is gone".
    print(f"apidiff: {baseline} -> working tree (declared version {version})")

    for finding in unresolved:
        print(finding)

    changes = surface_delta(before, after)
    promising = [c for c in changes if c.promises]

    for change in changes:
        print(change)

    for breakage in breakages:
        print(_render(breakage))

    print(
        f"\n{len(promising)} change(s) to promised surface, "
        f"{len(changes) - len(promising)} internal, {len(breakages)} breakage(s)"
    )

    if version.major < 1:
        print(
            "pre-1.0: reported, not enforced. The contract permits an "
            "incompatible public change in a minor release until 1.0.",
            file=sys.stderr,
        )
        return 1 if unresolved else 0

    return 1 if (breakages or unresolved) else 0


if __name__ == "__main__":
    sys.exit(app())
