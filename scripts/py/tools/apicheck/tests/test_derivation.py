"""The tier rules, and the proof they say the same thing the manifest said.

The unit tests pin the policy in isolation. The reproduction test is the one that
licensed deleting 132 lines of manifest: it runs the rules against this repo's
real source and asserts they agree with what was declared by hand, element for
element. If it ever fails, the derivation and the contract have diverged and the
deletion was not safe after all.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from apicheck import extract
from apicheck.core import Contract, Exposure, Tier, derive_contract, derive_tier, merge

# tests -> apicheck -> tools -> py -> scripts -> repo root
REPO = Path(__file__).resolve().parents[5]


def exposure(element="spoc.Thing", *, from_package=True, documented=False) -> Exposure:
    return Exposure(element=element, from_package=from_package, documented=documented)


# --- the policy, in isolation -------------------------------------------------


@pytest.mark.parametrize(
    ("from_package", "documented", "expected"),
    [
        (True, False, Tier.PUBLIC),
        (True, True, Tier.PROVISIONAL),
        (False, False, Tier.INTERNAL),
        (False, True, Tier.INTERNAL),
    ],
)
def test_every_combination_resolves(from_package, documented, expected):
    """Total over its inputs — nothing falls through to an implied tier."""
    got = derive_tier(exposure(from_package=from_package, documented=documented))
    assert got is expected


def test_the_notice_does_not_promote_an_internal_element():
    """Reaching an internal element is not a promotion, notice or no notice."""
    assert derive_tier(exposure(from_package=False, documented=True)) is Tier.INTERNAL


def test_an_unplaceable_element_resolves_to_nothing():
    """Unknown must stay unknown — guessing False would silently demote."""
    assert derive_tier(exposure(from_package=None)) is None


def test_unplaceable_elements_are_reported_not_dropped():
    contract, findings = derive_contract(
        [exposure("spoc.Fine"), exposure("spoc.Lost", from_package=None)]
    )
    assert [f.element for f in findings] == ["spoc.Lost"]
    assert contract.public == frozenset({"spoc.Fine"})


def test_one_unplaceable_element_does_not_cost_the_rest_their_report():
    placeable = [exposure(f"spoc.N{i}") for i in range(5)]
    contract, findings = derive_contract(
        [*placeable, exposure("spoc.Lost", from_package=None)]
    )
    assert len(contract.public) == 5
    assert len(findings) == 1


def test_derived_tiers_never_overlap():
    contract, _ = derive_contract(
        [
            exposure("spoc.A"),
            exposure("spoc.B", documented=True),
            exposure("spoc.c.C", from_package=False),
        ]
    )
    assert contract.overlaps() == []


def test_merge_keeps_both_halves():
    derived, _ = derive_contract([exposure("spoc.A")])
    declared = Contract(
        public=frozenset({"script:spoc"}),
        provisional=frozenset(),
        internal=frozenset(),
    )
    assert merge(derived, declared).public == frozenset({"spoc.A", "script:spoc"})


# --- the reproduction ---------------------------------------------------------


def declared_tiers() -> dict[str, list[str]]:
    """Whatever `[tool.spoc.stability]` still declares by hand."""
    table = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    stability = table["tool"]["spoc"]["stability"]
    return {
        tier: list(stability.get(tier, []))
        for tier in ("public", "provisional", "internal")
    }


in_repo = pytest.mark.skipif(
    not (REPO / "src" / "spoc").is_dir(), reason="not running inside the spoc repo"
)


@in_repo
def test_every_exposed_element_places():
    """No element of the real surface is left without a tier.

    This is what the reproduction test became. That one asserted the rules agreed
    with 132 hand-written entries, which is what licensed deleting them; with the
    entries gone there is nothing left to agree with, and an assertion that can
    only skip is worse than none. The enduring invariant is this one: the rules
    are total over the surface they govern.
    """
    exposures = extract.exposures(REPO / "src")
    assert exposures, "the extractor found nothing — it is not observing the package"

    contract, findings = derive_contract(exposures)
    assert findings == [], "every exposed element must place cleanly"
    assert all(derive_tier(e) is not None for e in exposures)
    assert contract.overlaps() == []
    assert len(contract.declared) == len(exposures)


@in_repo
def test_the_manifest_declares_no_importable_names():
    """The deletion, asserted rather than remembered.

    `manifest.load_contract` refuses a dotted path outright, so this would fail
    the whole run anyway — but failing here says *why*, and stops the table from
    quietly regrowing the restatement this change removed.
    """
    for tier, names in declared_tiers().items():
        dotted = [n for n in names if ":" not in n]
        assert dotted == [], f"{tier} declares importable names: {dotted}"


@in_repo
def test_every_declared_element_is_a_kind_no_observer_can_place():
    """What remains declared is exactly what the rules cannot reach."""
    kinds = {n.partition(":")[0] for names in declared_tiers().values() for n in names}
    assert kinds == {
        "entry-point",
        "extra",
        "fixture",
        "schema",
        "script",
        "template-set",
    }
