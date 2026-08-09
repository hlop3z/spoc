"""The cross-release delta: what appeared, what vanished, what changed tier.

Pure set arithmetic over two contracts, so these need no git and no repository.
Whether a difference is *breaking* is griffe's judgement, not this module's —
nothing here asserts on breakages.
"""

from __future__ import annotations

import pytest
from apicheck.core import Change, Contract, SurfaceChange, Tier, surface_delta


def contract(public=(), provisional=(), internal=()) -> Contract:
    return Contract(
        public=frozenset(public),
        provisional=frozenset(provisional),
        internal=frozenset(internal),
    )


def test_nothing_changed_yields_nothing():
    before = contract(public=["spoc.Framework"])
    assert surface_delta(before, before) == []


def test_a_newly_exposed_public_element_is_reported():
    """The event that replaced the manifest as the place a promise gets noticed."""
    result = surface_delta(contract(), contract(public=["spoc.New"]))
    assert result == [SurfaceChange(Change.ADDED, "spoc.New", after=Tier.PUBLIC)]
    assert result[0].promises is True


def test_a_newly_exposed_provisional_element_is_reported():
    result = surface_delta(contract(), contract(provisional=["spoc.scaffold.New"]))
    assert result[0].change is Change.ADDED
    assert result[0].after is Tier.PROVISIONAL
    assert result[0].promises is True


def test_a_removed_public_element_is_reported():
    result = surface_delta(contract(public=["spoc.Gone"]), contract())
    assert result == [SurfaceChange(Change.REMOVED, "spoc.Gone", before=Tier.PUBLIC)]
    assert result[0].promises is True


def test_an_internal_element_appearing_promises_nothing():
    """Internal churn is not a reviewable event — that tier promises nothing."""
    result = surface_delta(contract(), contract(internal=["spoc.cli.helper"]))
    assert result[0].change is Change.ADDED
    assert result[0].promises is False


def test_a_tier_change_is_reported_with_both_sides():
    result = surface_delta(
        contract(provisional=["spoc.scaffold.Cache"]),
        contract(public=["spoc.scaffold.Cache"]),
    )
    assert result == [
        SurfaceChange(
            Change.RETIERED,
            "spoc.scaffold.Cache",
            before=Tier.PROVISIONAL,
            after=Tier.PUBLIC,
        )
    ]
    assert result[0].promises is True


def test_a_demotion_to_internal_still_promises():
    """Lowering a tier is itself an incompatible change, so it must surface."""
    result = surface_delta(
        contract(public=["spoc.Thing"]), contract(internal=["spoc.Thing"])
    )
    assert result[0].change is Change.RETIERED
    assert result[0].promises is True


def test_non_import_elements_take_part():
    result = surface_delta(contract(public=["script:spoc"]), contract())
    assert result[0].element == "script:spoc"


def test_changes_are_deterministically_ordered():
    args = (
        contract(public=["spoc.B", "spoc.A"]),
        contract(public=["spoc.C"], internal=["spoc.D"]),
    )
    assert surface_delta(*args) == surface_delta(*args)


def test_every_change_renders_ascii_only():
    changes = surface_delta(
        contract(public=["spoc.Gone"], provisional=["spoc.Moved"]),
        contract(public=["spoc.Moved", "spoc.New"]),
    )
    for change in changes:
        str(change).encode("ascii")  # raises if a non-ASCII glyph crept in


@pytest.mark.parametrize(
    ("tiers", "expected"),
    [
        ({"public": ["a"]}, Tier.PUBLIC),
        ({"provisional": ["a"]}, Tier.PROVISIONAL),
        ({"internal": ["a"]}, Tier.INTERNAL),
        # A contradiction resolves to the strongest promise rather than the
        # weakest, so a contract that disagrees with itself never quietly reads
        # as promising less. `overlaps()` reports the contradiction separately.
        ({"public": ["a"], "internal": ["a"]}, Tier.PUBLIC),
    ],
)
def test_tiers_maps_every_element(tiers, expected):
    assert contract(**tiers).tiers()["a"] is expected
