"""The diff between a declared stability contract and an observed surface.

Pure: no I/O, no introspection, no knowledge of griffe or TOML. It is handed two
values and returns findings (Rule 2 — the adapters in this package do the
reaching out, this module only decides).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# A `provisional` element must say so in its own documentation, so that opting
# into it is deliberate. This is the phrase the check looks for.
PROVISIONAL_NOTICE = "may change incompatibly in a minor release"

# A withdrawal notice must name what replaces the element, or say that nothing
# does. This is the phrase that says it outright, for the second case.
NO_REPLACEMENT_NOTICE = "no replacement"

# A dotted path, which is how a withdrawal notice names a replacement.
_DOTTED = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


# Elements a dotted Python path cannot name carry a `kind:` prefix.
PYTHON = "python"


def states_settling_condition(doc: str) -> bool:
    """Whether a provisional notice says anything beyond the bare hedge.

    The contract requires a `provisional` element to state what would settle its
    tier — the open question, or the condition under which it becomes `public`
    or is withdrawn. That distinguishes a tier deliberately left open from one
    that was never decided, which is the failure this catches: the same
    boilerplate sentence pasted onto everything the author had not thought about
    yet.

    **This can only detect a bare hedge.** Whether a stated condition is
    *meaningful* is not mechanically decidable, and no amount of pattern
    matching will make it so — "settles eventually" passes. The check is worth
    having anyway, because the real failure mode is not a vacuous condition,
    it is the absence of one: a notice nobody wrote a second sentence for.
    """
    lowered = doc.lower()
    position = lowered.find(PROVISIONAL_NOTICE)
    if position == -1:
        return False
    remainder = doc[position + len(PROVISIONAL_NOTICE) :]
    # Strip what merely closes the boilerplate sentence, then see if anything
    # of substance is left. A word is the bar; punctuation and whitespace are not.
    return any(character.isalpha() for character in remainder)


def states_replacement(message: str, element: str) -> bool:
    """Whether a withdrawal notice says where to go instead.

    The contract requires a withdrawal to name what replaces the element, or to
    state that nothing does. A notice that does neither leaves a consumer with a
    warning and nowhere to act on it, which is the failure this catches.

    A replacement is named by a dotted path other than the element's own — the
    element names itself in nearly every notice worth writing, so its own path
    proves nothing. Saying there is no replacement is the explicit alternative.

    **This can only detect a bare omission**, on exactly the reasoning
    `states_settling_condition` records: whether a named path is the *right*
    replacement is not mechanically decidable, and pattern matching will never
    make it so. The failure worth catching is the notice nobody finished.
    """
    if NO_REPLACEMENT_NOTICE in message.lower():
        return True
    return any(path != element for path in _DOTTED.findall(message))


class Kind(StrEnum):
    """What went wrong. Everything but `UNVERIFIABLE` fails the check."""

    UNDECLARED = "undeclared"
    ABSENT = "absent"
    UNRESOLVED = "unresolved-tier"
    UNSETTLED = "unsettled-tier"
    UNREPLACED = "unreplaced-withdrawal"
    UNSANCTIONED = "unsanctioned-withdrawal"
    UNVERIFIABLE = "unverifiable"


class Tier(StrEnum):
    """The three promises. Ordered strongest to weakest."""

    PUBLIC = "public"
    PROVISIONAL = "provisional"
    INTERNAL = "internal"


@dataclass(frozen=True, order=True)
class Finding:
    """One divergence between the contract and the artifact."""

    kind: Kind
    element: str
    detail: str

    @property
    def fatal(self) -> bool:
        """True when this finding must fail the run.

        `UNVERIFIABLE` is reported but never fatal: it means the observer has no
        way to see that kind of element, which is a gap in coverage rather than a
        divergence. It is still printed — a check that silently skips what it
        cannot inspect reads as "everything passed" when it isn't.
        """
        return self.kind is not Kind.UNVERIFIABLE

    def __str__(self) -> str:
        # ASCII only: this prints to a Windows console under cp1252, where an
        # em-dash comes out as a replacement character.
        return f"{self.kind.value}: {self.element} - {self.detail}"


@dataclass(frozen=True)
class Contract:
    """The declared tiers. One element belongs to exactly one of them."""

    public: frozenset[str]
    provisional: frozenset[str]
    internal: frozenset[str]

    @property
    def declared(self) -> frozenset[str]:
        return self.public | self.provisional | self.internal

    def tiers(self) -> dict[str, Tier]:
        """Every element mapped to its tier.

        An element declared in two tiers resolves to the strongest, so a
        contradiction never silently reads as the weaker promise. `overlaps()`
        is what reports the contradiction itself.
        """
        mapping: dict[str, Tier] = {}
        for tier, members in (
            (Tier.INTERNAL, self.internal),
            (Tier.PROVISIONAL, self.provisional),
            (Tier.PUBLIC, self.public),
        ):
            mapping.update(dict.fromkeys(members, tier))
        return mapping

    def overlaps(self) -> list[tuple[str, tuple[str, ...]]]:
        """Elements declared in more than one tier — the contract contradicting itself."""
        tiers = {
            "public": self.public,
            "provisional": self.provisional,
            "internal": self.internal,
        }
        found = []
        for element in sorted(self.declared):
            names = tuple(n for n, members in tiers.items() if element in members)
            if len(names) > 1:
                found.append((element, names))
        return found


@dataclass(frozen=True)
class Observation:
    """What the artifact actually exposes.

    `verified_kinds` is the honest part: the observer states which kinds of
    element it was able to look at, so the core can tell "this element is gone"
    apart from "nobody looked".

    There is no `documented` set here any more. It existed to catch a
    `provisional` element whose documentation omitted the notice — a divergence
    that cannot occur now that the notice is what *makes* an element
    provisional. Keeping the check would have meant asking whether a fact agrees
    with itself, and it would have fired spuriously on a declared non-import
    element, which has no documentation to read.
    """

    elements: frozenset[str]
    verified_kinds: frozenset[str]


@dataclass(frozen=True, order=True)
class Withdrawal:
    """An element's mark for withdrawal, and whether that mark is complete.

    Deliberately *not* a `Tier`. A marked element keeps the tier it carried and
    every promise that tier makes until the release that removes it — that is
    the whole point of the waiting period, and a fourth tier would report the
    promise as dropped a full release before it actually is.
    """

    message: str
    """The notice a consumer sees when they reach the element."""

    replacement_stated: bool = False
    """Whether that notice names a replacement, or says there is none."""


@dataclass(frozen=True, order=True)
class Exposure:
    """How the artifact exposes one importable element.

    Only the facts the rules need. An adapter supplies these by reading the
    source; this module never learns where they came from.
    """

    element: str

    from_package: bool | None
    """Whether the module exposing it is a package rather than a plain module.

    `None` means the observer could not tell — which is not the same as `False`,
    and must not be silently read as one. An element it cannot place has no
    derivable tier, and the check says so rather than guessing `internal`.
    """

    documented: bool
    """Whether its own documentation carries `PROVISIONAL_NOTICE`."""

    settling_stated: bool = False
    """Whether that notice goes on to say what would settle the tier.

    Only consulted for an element the notice made `provisional`; meaningless
    otherwise, and left `False` there rather than given a third state.
    """

    withdrawal: Withdrawal | None = None
    """Its mark for withdrawal, or `None` when it carries none.

    Read beside the tier, never instead of it: `derive_tier` does not consult
    this field, because entering the lifecycle changes nothing about what the
    element currently promises.
    """


def derive_tier(exposure: Exposure) -> Tier | None:
    """The tier the rules assign, or `None` when they cannot resolve one.

    The whole policy, in one place:

    - exposed from a plain module, not a package -> `internal`. The object's
      public location is the package that re-exports it; the deeper path is the
      definition site, and reaching it is not a promotion.
    - carries the provisional notice -> `provisional`.
    - anything else exposed from a package -> `public`.

    Total over the facts it is given, so no element falls through to an implied
    tier. The one gap is an unplaceable element, which returns `None` and is
    reported rather than assumed.
    """
    if exposure.from_package is None:
        return None
    if not exposure.from_package:
        return Tier.INTERNAL
    return Tier.PROVISIONAL if exposure.documented else Tier.PUBLIC


def derive_contract(exposures: list[Exposure]) -> tuple[Contract, list[Finding]]:
    """Build the contract the rules imply, naming everything they could not place.

    Returns the contract alongside its findings rather than raising: a single
    unplaceable element should not cost the run its report on the other several
    hundred.
    """
    tiers: dict[Tier, set[str]] = {tier: set() for tier in Tier}
    findings: list[Finding] = []

    for exposure in sorted(exposures):
        tier = derive_tier(exposure)
        if tier is None:
            findings.append(
                Finding(
                    Kind.UNRESOLVED,
                    exposure.element,
                    "exposed, but the observer could not tell whether it comes "
                    "from a package, so no tier follows",
                )
            )
            continue
        if tier is Tier.PROVISIONAL and not exposure.settling_stated:
            findings.append(
                Finding(
                    Kind.UNSETTLED,
                    exposure.element,
                    "provisional, but its notice does not say what would settle "
                    "the tier - state the open question, or the condition under "
                    "which it becomes public or is withdrawn",
                )
            )
        if exposure.withdrawal and not exposure.withdrawal.replacement_stated:
            findings.append(
                Finding(
                    Kind.UNREPLACED,
                    exposure.element,
                    "marked for withdrawal, but its notice names no replacement "
                    "and does not say there is none - a consumer who is warned "
                    "needs somewhere to go",
                )
            )
        tiers[tier].add(exposure.element)

    contract = Contract(
        public=frozenset(tiers[Tier.PUBLIC]),
        provisional=frozenset(tiers[Tier.PROVISIONAL]),
        internal=frozenset(tiers[Tier.INTERNAL]),
    )
    return contract, findings


def merge(derived: Contract, declared: Contract) -> Contract:
    """The full contract: rules for importable names, declaration for the rest.

    The two never overlap by construction — the derivation only ever sees
    importable elements, and the declaration only ever holds the kinds no static
    observer can attribute a tier to.
    """
    return Contract(
        public=derived.public | declared.public,
        provisional=derived.provisional | declared.provisional,
        internal=derived.internal | declared.internal,
    )


class Change(StrEnum):
    """How one element differs between two releases."""

    ADDED = "added"
    REMOVED = "removed"
    RETIERED = "retiered"


@dataclass(frozen=True, order=True)
class SurfaceChange:
    """One element's difference between a baseline surface and this one."""

    change: Change
    element: str
    before: Tier | None = None
    after: Tier | None = None

    @property
    def promises(self) -> bool:
        """True when a stability promise is involved on either side.

        An `internal` element appearing or vanishing is not a reviewable event —
        that tier promises nothing. Growth of the *promised* surface is, which is
        what replaced the manifest as the place a new promise gets noticed.
        """
        return any(
            tier in (Tier.PUBLIC, Tier.PROVISIONAL)
            for tier in (self.before, self.after)
        )

    def __str__(self) -> str:
        # ASCII only: this prints to a Windows console under cp1252.
        match self.change:
            case Change.ADDED:
                return f"added: {self.element} ({self.after})"
            case Change.REMOVED:
                return f"removed: {self.element} (was {self.before})"
            case _:
                return f"retiered: {self.element} ({self.before} -> {self.after})"


def surface_delta(before: Contract, after: Contract) -> list[SurfaceChange]:
    """Every element that appeared, vanished, or changed tier between the two.

    Pure set arithmetic over two contracts. It says nothing about whether a
    difference is *breaking* — that judgement needs signatures, not names, and
    belongs to the adopted differ.
    """
    was, now = before.tiers(), after.tiers()

    changes = [
        SurfaceChange(Change.ADDED, element, after=now[element])
        for element in now.keys() - was.keys()
    ]
    changes += [
        SurfaceChange(Change.REMOVED, element, before=was[element])
        for element in was.keys() - now.keys()
    ]
    changes += [
        SurfaceChange(Change.RETIERED, element, before=was[element], after=now[element])
        for element in was.keys() & now.keys()
        if was[element] != now[element]
    ]
    return sorted(changes)


MinorLine = tuple[int, int]
"""A release's `(major, minor)`. The unit the waiting period is counted in.

Not a version: the policy measures the wait in minor releases, so a patch
release must not be able to satisfy it. Reducing a version to its minor line
here is what makes that structural rather than a condition someone can forget.
"""


@dataclass(frozen=True, order=True)
class ReleasePresence:
    """How one published release exposed an element.

    Supplied by the adapter that reads published releases; this module never
    learns what a tag is.
    """

    line: MinorLine
    present: bool
    withdrawn: bool


class Lifecycle(StrEnum):
    """Whether a removal completed the withdrawal lifecycle."""

    COMPLIANT = "compliant"
    VIOLATED = "violated"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, order=True)
class LifecycleVerdict:
    """One removal, judged against the published releases behind it."""

    lifecycle: Lifecycle
    element: str
    detail: str

    @property
    def justified(self) -> bool:
        """True only for a removal shown to have completed the lifecycle.

        `UNDETERMINED` is not justified. "Nobody could tell" must never be
        reported as "the lifecycle was completed" — the same direction the
        unverifiable-kind rule already protects.
        """
        return self.lifecycle is Lifecycle.COMPLIANT

    def __str__(self) -> str:
        # ASCII only: this prints to a Windows console under cp1252.
        return f"{self.lifecycle.value}: {self.element} - {self.detail}"


def lifecycle_verdict(
    element: str, history: list[ReleasePresence], removed_in: MinorLine
) -> LifecycleVerdict:
    """Judge a removal against what the published releases actually show.

    `history` is the element's presence at every published release older than
    `removed_in`; order does not matter, and the caller may supply as few as it
    could read. The three answers are deliberately distinct: a removal that
    completed the lifecycle, one shown not to have, and one the record cannot
    settle either way.

    The rule, from the release policy: the element must have been marked in an
    earlier release, and at least one full minor release must have shipped in
    between with the element still functional. A release still carrying the
    element is functional whether or not it also carries the mark, so presence
    is the bar for the in-between release — the mark's job was done the moment
    it first appeared.
    """
    if not history:
        return LifecycleVerdict(
            Lifecycle.UNDETERMINED,
            element,
            "no published release could be read, so there is no record of a "
            "mark to check the removal against",
        )

    marked = [
        release.line for release in history if release.present and release.withdrawn
    ]
    if not marked:
        return LifecycleVerdict(
            Lifecycle.VIOLATED,
            element,
            "removed, but no published release carried a mark for it",
        )

    first_marked = min(marked)
    between = {
        release.line
        for release in history
        if release.present and first_marked < release.line < removed_in
    }
    if between:
        return LifecycleVerdict(
            Lifecycle.COMPLIANT,
            element,
            f"marked in {_render(first_marked)}, still shipped in "
            f"{', '.join(sorted(_render(line) for line in between))}, "
            f"removed in {_render(removed_in)}",
        )

    # Nothing shipped in between. Whether that is a violation depends on
    # whether the record actually reaches back past the mark: if the oldest
    # release we could read is already marked, the mark may have appeared
    # earlier still, and the answer is not ours to give.
    oldest = min(release.line for release in history)
    if first_marked <= oldest:
        return LifecycleVerdict(
            Lifecycle.UNDETERMINED,
            element,
            f"marked as far back as the record goes ({_render(oldest)}), so the "
            "release that first marked it cannot be established",
        )

    return LifecycleVerdict(
        Lifecycle.VIOLATED,
        element,
        f"marked in {_render(first_marked)} and removed in "
        f"{_render(removed_in)}, with no full minor release in between - a "
        "patch release does not satisfy the waiting period",
    )


def _render(line: MinorLine) -> str:
    """A minor line as a reader writes it."""
    return f"{line[0]}.{line[1]}"


def kind_of(element: str) -> str:
    """The element's kind — the `kind:` prefix, or `python` for a dotted path."""
    prefix, sep, _ = element.partition(":")
    return prefix if sep else PYTHON


def diff(contract: Contract, observed: Observation) -> list[Finding]:
    """Every divergence between what is declared and what exists."""
    findings: list[Finding] = []

    for element, tiers in contract.overlaps():
        findings.append(
            Finding(
                Kind.UNDECLARED,
                element,
                f"declared in more than one tier ({', '.join(tiers)})",
            )
        )

    for element in sorted(contract.declared):
        if kind_of(element) not in observed.verified_kinds:
            findings.append(
                Finding(
                    Kind.UNVERIFIABLE,
                    element,
                    f"no observer covers kind '{kind_of(element)}'",
                )
            )
        elif element not in observed.elements:
            findings.append(
                Finding(
                    Kind.ABSENT, element, "declared in the contract but not exposed"
                )
            )

    for element in sorted(observed.elements - contract.declared):
        findings.append(
            Finding(
                Kind.UNDECLARED,
                element,
                "exposed by the artifact but absent from the contract",
            )
        )

    return sorted(findings)


def exit_code(findings: list[Finding]) -> int:
    """0 when nothing fatal was found."""
    return 1 if any(f.fatal for f in findings) else 0
