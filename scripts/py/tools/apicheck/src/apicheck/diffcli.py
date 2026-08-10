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

From 1.0 the increment matters too. A breaking change is what a major release is
for, so breakages are permitted there and refused everywhere else; an incomplete
withdrawal is refused in every increment, because completing the lifecycle is
what earns the removal a major release is allowed to make.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import cyclopts
import griffe

from apicheck import extract
from apicheck.core import (
    Change,
    Exposure,
    Lifecycle,
    LifecycleVerdict,
    derive_contract,
    derive_tier,
    lifecycle_verdict,
    surface_delta,
)
from apicheck.release import (
    GitError,
    declared_version,
    latest_tag,
    minor_line,
    source_at,
    tag_version,
    withdrawal_history,
)

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


def _verdicts(
    repo: Path, changes: list, removed_in, package: str = "spoc"
) -> list[LifecycleVerdict]:
    """Judge every removal that took a promise with it.

    Driven by the removals rather than run over the whole surface: an element
    that is still exposed has nothing to answer for, and an `internal` one never
    promised anything. In the ordinary case — nothing promised was removed —
    this reaches for no releases at all.
    """
    return [
        lifecycle_verdict(
            change.element,
            withdrawal_history(
                repo, change.element, before=removed_in, package=package
            ),
            removed_in=removed_in,
        )
        for change in changes
        if change.change is Change.REMOVED and change.promises
    ]


def _in_flight(exposures: list[Exposure]) -> list[str]:
    """Elements marked for withdrawal but still exposed, with their tier.

    Printed because a withdrawal in progress is the state the release policy
    cares most about and the one nothing else in this output would show. The
    tier is named first and in full: entering the lifecycle changes nothing
    about what the element currently promises.
    """
    return sorted(
        f"withdrawing: {exposure.element} (still {derive_tier(exposure)})"
        for exposure in exposures
        if exposure.withdrawal is not None and derive_tier(exposure) is not None
    )


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

    exposures = extract.exposures(repo / "src")
    after, unresolved = derive_contract(exposures)

    # Always say what was compared. A silent baseline is the same trap as
    # reporting "nobody looked" as "it is gone".
    print(f"apidiff: {baseline} -> working tree (declared version {version})")

    for finding in unresolved:
        print(finding)

    changes = surface_delta(before, after)
    promising = [c for c in changes if c.promises]

    for change in changes:
        print(change)

    for line in _in_flight(exposures):
        print(line)

    try:
        verdicts = _verdicts(repo, changes, minor_line(version))
    except GitError as exc:
        print(f"apidiff: {exc}", file=sys.stderr)
        return 2

    for verdict in verdicts:
        print(verdict)

    for breakage in breakages:
        print(_render(breakage))

    violations = [v for v in verdicts if v.lifecycle is Lifecycle.VIOLATED]
    undetermined = [v for v in verdicts if v.lifecycle is Lifecycle.UNDETERMINED]

    summary = (
        f"\n{len(promising)} change(s) to promised surface, "
        f"{len(changes) - len(promising)} internal, {len(breakages)} breakage(s)"
    )
    if verdicts:
        summary += (
            f", {len(violations)} incomplete withdrawal(s), "
            f"{len(undetermined)} undetermined"
        )
    print(summary)

    if version.major < 1:
        print(
            "pre-1.0: reported, not enforced. The contract permits an "
            "incompatible public change in a minor release until 1.0, and "
            "withdrawing without a completed lifecycle with it.",
            file=sys.stderr,
        )
        return 1 if unresolved else 0

    # An undetermined history is not a failed check, it is a check that did not
    # finish — the same thing an unresolvable baseline means, so it gets the
    # same code. What must never happen is either of them returning 0.
    if undetermined:
        return 2

    # A violation is fatal whatever increment is claimed. A major release is
    # permitted to remove a `public` element; it is not permitted to skip the
    # lifecycle that earns the removal.
    if violations or unresolved:
        return 1

    # Breaking changes are what a major release is *for* — the lifecycle exists
    # to make one legitimate. Failing on them regardless of increment would
    # leave no version this project could ever cut a removal in.
    baseline_version = tag_version(baseline)
    major_release = (
        baseline_version is not None and version.major > baseline_version.major
    )
    if major_release and breakages:
        print(
            f"major release ({baseline_version} -> {version}): "
            f"{len(breakages)} incompatible change(s) permitted",
            file=sys.stderr,
        )
        return 0

    return 1 if breakages else 0


if __name__ == "__main__":
    sys.exit(app())
