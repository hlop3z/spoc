"""The diff core is the gate's decision-maker, so every finding type is pinned.

Pure inputs, pure outputs — no filesystem, no griffe, no package under test.
"""

from __future__ import annotations

import pytest
from apicheck.core import (
    PROVISIONAL_NOTICE,
    Contract,
    Finding,
    Kind,
    Observation,
    diff,
    exit_code,
    kind_of,
)

ALL_KINDS = frozenset({"python", "script", "extra"})


def contract(public=(), provisional=(), internal=()) -> Contract:
    return Contract(
        public=frozenset(public),
        provisional=frozenset(provisional),
        internal=frozenset(internal),
    )


def observation(elements=(), kinds=ALL_KINDS) -> Observation:
    return Observation(
        elements=frozenset(elements),
        verified_kinds=frozenset(kinds),
    )


def kinds_found(findings: list[Finding]) -> set[Kind]:
    return {f.kind for f in findings}


def test_conformant_surface_yields_nothing():
    result = diff(
        contract(public=["spoc.Framework"], internal=["spoc.cli.main"]),
        observation(elements=["spoc.Framework", "spoc.cli.main"]),
    )
    assert result == []
    assert exit_code(result) == 0


def test_undeclared_element_is_fatal():
    result = diff(
        contract(public=["spoc.Framework"]),
        observation(elements=["spoc.Framework", "spoc.Surprise"]),
    )
    assert kinds_found(result) == {Kind.UNDECLARED}
    assert result[0].element == "spoc.Surprise"
    assert exit_code(result) == 1


def test_declared_but_absent_element_is_fatal():
    result = diff(
        contract(public=["spoc.Framework", "spoc.Gone"]),
        observation(elements=["spoc.Framework"]),
    )
    assert kinds_found(result) == {Kind.ABSENT}
    assert result[0].element == "spoc.Gone"
    assert exit_code(result) == 1


def test_provisional_element_is_not_second_guessed():
    """The notice is what *makes* an element provisional, so the core no longer
    re-checks that a provisional element carries it. Asking whether a fact agrees
    with itself only ever produced false alarms on declared non-import elements,
    which have no documentation to read."""
    result = diff(
        contract(provisional=["spoc.scaffold.Cache"]),
        observation(elements=["spoc.scaffold.Cache"]),
    )
    assert result == []


def test_public_element_needs_no_notice():
    """The notice is a provisional obligation only — public must not demand it."""
    result = diff(
        contract(public=["spoc.Framework"]), observation(elements=["spoc.Framework"])
    )
    assert result == []


def test_unverified_kind_is_reported_but_not_fatal():
    result = diff(
        contract(public=["schema:config/spoc.toml"]),
        observation(elements=[], kinds=ALL_KINDS),
    )
    assert kinds_found(result) == {Kind.UNVERIFIABLE}
    assert result[0].fatal is False
    assert exit_code(result) == 0


def test_unverifiable_wins_over_absent():
    """An unwatched kind must never be reported as a removal."""
    result = diff(
        contract(public=["script:spoc"]),
        observation(elements=[], kinds=frozenset({"python"})),
    )
    assert kinds_found(result) == {Kind.UNVERIFIABLE}


def test_element_in_two_tiers_is_fatal():
    result = diff(
        contract(public=["spoc.Framework"], internal=["spoc.Framework"]),
        observation(elements=["spoc.Framework"]),
    )
    assert Kind.UNDECLARED in kinds_found(result)
    assert "more than one tier" in result[0].detail
    assert exit_code(result) == 1


def test_findings_accumulate_across_types():
    result = diff(
        contract(public=["spoc.Gone"], provisional=["spoc.scaffold.Cache"]),
        observation(elements=["spoc.scaffold.Cache", "spoc.Surprise"]),
    )
    assert kinds_found(result) == {Kind.ABSENT, Kind.UNDECLARED}


def test_undeclared_non_import_element_is_fatal():
    """The declared half still diverges in both directions — it is the only half
    that can, now that importable tiers are derived from the artifact itself."""
    result = diff(
        contract(public=["script:spoc"]),
        observation(elements=["script:spoc", "extra:surprise"]),
    )
    assert kinds_found(result) == {Kind.UNDECLARED}
    assert result[0].element == "extra:surprise"
    assert exit_code(result) == 1


def test_declared_but_absent_non_import_element_is_fatal():
    result = diff(
        contract(public=["script:spoc", "extra:gone"]),
        observation(elements=["script:spoc"]),
    )
    assert kinds_found(result) == {Kind.ABSENT}
    assert result[0].element == "extra:gone"
    assert exit_code(result) == 1


def test_findings_are_deterministically_ordered():
    args = (
        contract(public=["spoc.B", "spoc.A"]),
        observation(elements=["spoc.D", "spoc.C"]),
    )
    assert [f.element for f in diff(*args)] == [f.element for f in diff(*args)]


@pytest.mark.parametrize(
    ("element", "expected"),
    [
        ("spoc.Framework", "python"),
        ("spoc.formats.loads", "python"),
        ("script:spoc", "script"),
        ("entry-point:pytest11.spoc", "entry-point"),
        ("template-set:default", "template-set"),
    ],
)
def test_kind_is_read_from_the_prefix(element, expected):
    assert kind_of(element) == expected


def test_notice_phrase_is_stated_once():
    """The phrase is the contract between the checker and the docstrings."""
    assert PROVISIONAL_NOTICE == "may change incompatibly in a minor release"
