"""Thin CLI adapter for the cross-release surface comparison (Rule 2).

Two questions, two answers, one command:

- *What changed?* — computed here from the derived tiers at both refs, so an
  addition is reported at the tier the element actually carries.
- *Was any of it breaking?* — delegated to griffe, which compares signatures
  rather than names. Classifying a breakage is not something to hand-roll.
- *Did it break a promise?* — answered here, not by griffe. griffe reads public
  as "not underscored"; this project reads it as a derived tier, and the two
  disagree about every leaf reachable at its definition site but exported from
  nowhere. The tier is what gates, so a shape change inside `spoc.scaffold.errors`
  is reported without failing a release over a promise the contract never made.

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
    Tier,
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


def _load(src: Path, package: str = "spoc"):
    """The package as griffe reads it, without importing it.

    `allow_inspection=False` keeps the no-import invariant: griffe falls back to
    importing a module it cannot read statically, and a checker that imports its
    subject is auditing whatever happens to be installed.
    """
    return griffe.load(package, search_paths=[str(src)], allow_inspection=False)


def _breakages(old, new) -> list:
    """Incompatible changes between two loaded trees, classified by griffe."""
    return list(griffe.find_breaking_changes(old, new))


def _exposure_paths(module, seen: set[str] | None = None) -> dict[str, set[str]]:
    """Every definition site mapped to the paths that expose it.

    griffe names a breakage by its *canonical* path — where the object is
    defined. The contract names elements by where they are *exposed*, because
    that is what a caller imports. For a re-exported element the two differ
    (`spoc.core.declaration.component` against `spoc.component`), so a lookup by
    canonical path alone would find no tier for the very elements that carry the
    strongest promises, and report a broken one as unpromised.

    One definition can have several exposures; all are kept, and the caller takes
    the strongest tier among them.
    """
    seen = set() if seen is None else seen
    paths: dict[str, set[str]] = {}
    if module.path in seen:
        return paths
    seen.add(module.path)

    for member in module.members.values():
        name = getattr(member, "name", "")
        if name.startswith("_"):
            continue
        try:
            canonical_path = member.canonical_path
        except griffe.AliasResolutionError:
            # An alias to something outside the package — `spoc.logging` is the
            # standard library's. Reading its canonical path is what forces the
            # resolution that fails. It cannot carry a tier in this package's
            # contract either, so there is nothing to map.
            continue
        paths.setdefault(canonical_path, set()).add(member.path)
        # Submodules are walked, aliases are not: an alias's target lives in the
        # module that defines it, which this walk reaches on its own.
        if getattr(member, "is_module", False) and not getattr(
            member, "is_alias", False
        ):
            for canonical, exposed in _exposure_paths(member, seen).items():
                paths.setdefault(canonical, set()).update(exposed)
    return paths


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


#: What a breakage is reported as when the contract has no tier for the element
#: griffe named. Not a tier: it says the two disagree about what the surface even
#: contains, which is a different fact from a tier being weak.
_UNTIERED = "not in the contract"


#: Strongest first: an element exposed twice is judged by the stronger promise,
#: for the same reason `Contract.tiers` resolves an overlap that way — a
#: contradiction must never silently read as the weaker one.
_STRONGEST = (Tier.PUBLIC, Tier.PROVISIONAL, Tier.INTERNAL)


def _tier_of(breakage, tiers: dict[str, Tier], exposures: dict[str, set[str]]):
    """The tier the element carried in the baseline, as this project derives it.

    griffe decides *whether* something broke, which is the part worth delegating.
    It cannot decide whether the broken thing was ever promised: its notion of
    public is "not underscored", where this project's is a derived tier, and the
    two disagree about every leaf reachable at its definition site but exported
    from nowhere. Reporting griffe's word alone makes a removal from
    `spoc.scaffold.errors` read as a broken promise the contract never made.

    Looked up through every path that exposes the definition, because the
    contract keys on the exposure and griffe names the definition.

    Returns `None` where the contract has no tier at all — said rather than
    guessed. An absent element is not an internal one: it means the surface walk
    never reached it, and calling that `internal` would be this tool agreeing
    with itself instead of reporting.
    """
    canonical = breakage.obj.canonical_path
    candidates = {
        tiers[path] for path in exposures.get(canonical, set()) if path in tiers
    }
    if canonical in tiers:
        candidates.add(tiers[canonical])
    return next((tier for tier in _STRONGEST if tier in candidates), None)


def _promised(breakage, tiers: dict[str, Tier], exposures: dict[str, set[str]]) -> bool:
    """Whether this breakage touched something the contract actually promised.

    Mirrors `SurfaceChange.promises`, and for the same reason: a change to an
    element that promises nothing is not a reviewable event, and counting it
    beside one that does hides the count that matters.
    """
    return _tier_of(breakage, tiers, exposures) in (Tier.PUBLIC, Tier.PROVISIONAL)


def _render(breakage, tiers: dict[str, Tier], exposures: dict[str, set[str]]) -> str:
    """One breakage as a plain line, qualified by the tier it broke.

    Built from the object rather than `explain()`, which embeds ANSI colour and
    the file path — and that path points into the throwaway directory the
    baseline was unpacked into, which means nothing to a reader. ASCII only, for
    the Windows console this project is developed on.
    """
    detail = str(getattr(breakage.kind, "value", breakage.kind))
    tier = _tier_of(breakage, tiers, exposures)
    return (
        f"breaking: {breakage.obj.canonical_path} "
        f"({tier if tier is not None else _UNTIERED}) - {detail.lower()}"
    )


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
            old_tree = _load(old_src)
            breakages = _breakages(old_tree, _load(repo / "src"))
            # Built from the baseline tree, to match the tiers it is read beside.
            exposure_paths = _exposure_paths(old_tree)
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

    # Judged against the tiers *before* the change: whether a promise was broken
    # is a question about what was promised, which is what the baseline held.
    before_tiers = before.tiers()
    promised_breakages = [
        b for b in breakages if _promised(b, before_tiers, exposure_paths)
    ]

    for breakage in breakages:
        print(_render(breakage, before_tiers, exposure_paths))

    violations = [v for v in verdicts if v.lifecycle is Lifecycle.VIOLATED]
    undetermined = [v for v in verdicts if v.lifecycle is Lifecycle.UNDETERMINED]

    summary = (
        f"\n{len(promising)} change(s) to promised surface, "
        f"{len(changes) - len(promising)} internal, "
        f"{len(promised_breakages)} breakage(s) to promised surface"
    )
    if len(breakages) != len(promised_breakages):
        summary += f", {len(breakages) - len(promised_breakages)} to unpromised"
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
    #
    # Only the promised ones gate. A tier that promises nothing has nothing to
    # break, so failing a minor release over a changed shape inside
    # `spoc.scaffold.errors` would enforce a promise the contract declines to
    # make — and would push the fix toward re-tiering the element rather than
    # reviewing the change. Unpromised breakages still print, with their tier.
    baseline_version = tag_version(baseline)
    major_release = (
        baseline_version is not None and version.major > baseline_version.major
    )
    if major_release and promised_breakages:
        print(
            f"major release ({baseline_version} -> {version}): "
            f"{len(promised_breakages)} incompatible change(s) permitted",
            file=sys.stderr,
        )
        return 0

    return 1 if promised_breakages else 0


if __name__ == "__main__":
    sys.exit(app())
