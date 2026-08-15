"""Judging a griffe breakage against this project's tiers.

griffe answers *whether* something broke. It cannot answer whether the broken
thing was ever promised: it reads public as "not underscored", where this project
reads it as a derived tier. These pin the translation between the two — including
the alias hop, without which every re-exported element (which is to say, every
element carrying the strongest promise) would look unpromised.

Pure lookups over two dicts, so these need no git, no griffe load, and no
repository.
"""

from __future__ import annotations

import pytest
from apicheck.core import Tier
from apicheck.diffcli import _UNTIERED, _promised, _render, _tier_of


class _Obj:
    def __init__(self, canonical_path: str) -> None:
        self.canonical_path = canonical_path


class _Breakage:
    """The two fields the tier lookup reads off a griffe breakage."""

    def __init__(
        self, canonical_path: str, kind: str = "Parameter was removed"
    ) -> None:
        self.obj = _Obj(canonical_path)
        self.kind = kind


def test_a_definition_that_is_its_own_exposure_is_found():
    tiers = {"spoc.scaffold.cli.register": Tier.INTERNAL}
    breakage = _Breakage("spoc.scaffold.cli.register")
    assert _tier_of(breakage, tiers, {}) is Tier.INTERNAL


def test_a_re_exported_element_is_found_through_its_exposure():
    """The case that matters most: the contract keys on the name a caller imports.

    Without the alias hop this returns `None`, and a genuinely broken `public`
    element is reported — and gated — as though it promised nothing.
    """
    tiers = {"spoc.component": Tier.PUBLIC}
    exposures = {"spoc.core.declaration.component": {"spoc.component"}}
    breakage = _Breakage("spoc.core.declaration.component")

    assert _tier_of(breakage, tiers, exposures) is Tier.PUBLIC
    assert _promised(breakage, tiers, exposures) is True


def test_an_element_the_contract_never_placed_has_no_tier():
    """An unexported error leaf: reachable at its definition site, promised nowhere."""
    breakage = _Breakage("spoc.scaffold.errors.RevisionUnavailableError")
    assert _tier_of(breakage, {}, {}) is None
    assert _promised(breakage, {}, {}) is False


def test_absent_is_reported_as_absent_rather_than_internal():
    """`None` and `internal` are different facts and must not collapse.

    An internal element was placed and promises nothing; an absent one was never
    placed, which says the two tools disagree about what the surface contains.
    """
    line = _render(_Breakage("spoc.nowhere.thing"), {}, {})
    assert _UNTIERED in line
    assert Tier.INTERNAL.value not in line


@pytest.mark.parametrize(
    ("tier", "promised"),
    [(Tier.PUBLIC, True), (Tier.PROVISIONAL, True), (Tier.INTERNAL, False)],
)
def test_only_the_promising_tiers_count_as_promised(tier, promised):
    tiers = {"spoc.Thing": tier}
    exposures = {"spoc.mod.Thing": {"spoc.Thing"}}
    assert _promised(_Breakage("spoc.mod.Thing"), tiers, exposures) is promised


def test_an_element_exposed_twice_is_judged_by_the_stronger_promise():
    """Same rule `Contract.tiers` uses for an overlap: never read as the weaker one."""
    tiers = {"spoc.Thing": Tier.PUBLIC, "spoc.extra.Thing": Tier.INTERNAL}
    exposures = {"spoc.mod.Thing": {"spoc.Thing", "spoc.extra.Thing"}}
    assert _tier_of(_Breakage("spoc.mod.Thing"), tiers, exposures) is Tier.PUBLIC


def test_the_rendered_line_names_the_tier_and_stays_ascii():
    tiers = {"spoc.component": Tier.PUBLIC}
    exposures = {"spoc.core.declaration.component": {"spoc.component"}}
    line = _render(_Breakage("spoc.core.declaration.component"), tiers, exposures)

    assert line == (
        "breaking: spoc.core.declaration.component (public) - parameter was removed"
    )
    line.encode("ascii")  # raises if a non-ASCII character ever creeps in
