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
    UNMARKED = "unmarked-provisional"
    UNVERIFIABLE = "unverifiable"


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
    """

    elements: frozenset[str]
    documented: frozenset[str]
    verified_kinds: frozenset[str]


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

    for element in sorted(contract.provisional & observed.elements):
        if element not in observed.documented:
            findings.append(
                Finding(
                    Kind.UNMARKED,
                    element,
                    f"provisional, but its documentation omits '{PROVISIONAL_NOTICE}'",
                )
            )

    return sorted(findings)


def exit_code(findings: list[Finding]) -> int:
    """0 when nothing fatal was found."""
    return 1 if any(f.fatal for f in findings) else 0
