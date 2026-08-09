"""The diff between a declared stability contract and an observed surface.

Pure: no I/O, no introspection, no knowledge of griffe or TOML. It is handed two
values and returns findings (Rule 2 — the adapters in this package do the
reaching out, this module only decides).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# A `provisional` element must say so in its own documentation, so that opting
# into it is deliberate. This is the phrase the check looks for.
PROVISIONAL_NOTICE = "may change incompatibly in a minor release"

# Elements a dotted Python path cannot name carry a `kind:` prefix.
PYTHON = "python"


class Kind(StrEnum):
    """What went wrong. Everything but `UNVERIFIABLE` fails the check."""

    UNDECLARED = "undeclared"
    ABSENT = "absent"
    UNRESOLVED = "unresolved-tier"
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
class Exposure:
    """How the artifact exposes one importable element.

    The two facts the rules need, and nothing else. An adapter supplies these by
    reading the source; this module never learns where they came from.
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
