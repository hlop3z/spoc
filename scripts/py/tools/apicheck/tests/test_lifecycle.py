"""The withdrawal lifecycle: whether a removal earned its way out.

Pure, so these need no git and no repository — the verdict is handed an
element's presence at each published release and answers from that alone. The
three outcomes are deliberately distinct, and the pair of tests that separate
`VIOLATED` from `UNDETERMINED` are the point of the whole module: a record that
does not reach back past the mark cannot convict, and must not acquit either.
"""

from __future__ import annotations

from apicheck.core import (
    Exposure,
    Kind,
    Lifecycle,
    ReleasePresence,
    Withdrawal,
    derive_contract,
    lifecycle_verdict,
    states_replacement,
)

ELEMENT = "spoc.scaffold.extract_archive"


def shipped(
    major: int, minor: int, *, present=True, withdrawn=False
) -> ReleasePresence:
    return ReleasePresence(line=(major, minor), present=present, withdrawn=withdrawn)


def withdrawn_exposure(message: str, *, replacement_stated: bool) -> Exposure:
    """A `public` element carrying a mark — the shape every tier test here needs."""
    return Exposure(
        element=ELEMENT,
        from_package=True,
        documented=False,
        withdrawal=Withdrawal(message=message, replacement_stated=replacement_stated),
    )


# --- the waiting period -------------------------------------------------


def test_a_removal_never_marked_is_a_violation():
    verdict = lifecycle_verdict(
        ELEMENT, [shipped(0, 5), shipped(0, 6), shipped(0, 7)], removed_in=(1, 0)
    )
    assert verdict.lifecycle is Lifecycle.VIOLATED
    assert verdict.justified is False
    assert "no published release carried a mark" in verdict.detail


def test_a_removal_marked_only_in_the_preceding_release_is_a_violation():
    """Marked in 0.7 and removed in 1.0 — nothing shipped in between."""
    verdict = lifecycle_verdict(
        ELEMENT,
        [shipped(0, 5), shipped(0, 6), shipped(0, 7, withdrawn=True)],
        removed_in=(1, 0),
    )
    assert verdict.lifecycle is Lifecycle.VIOLATED
    assert "no full minor release in between" in verdict.detail


def test_patch_releases_do_not_satisfy_the_waiting_period():
    """0.6.0 marks it, 0.6.1 and 0.6.2 ship, 1.0 removes it.

    Every patch of a minor line collapses to the same line, so three releases
    here are one release as far as the policy is concerned. This is the case a
    tag count would wave through.
    """
    verdict = lifecycle_verdict(
        ELEMENT,
        [
            shipped(0, 5),
            shipped(0, 6, withdrawn=True),
            shipped(0, 6, withdrawn=True),
            shipped(0, 6, withdrawn=True),
        ],
        removed_in=(1, 0),
    )
    assert verdict.lifecycle is Lifecycle.VIOLATED


def test_a_full_minor_line_in_between_completes_the_lifecycle():
    verdict = lifecycle_verdict(
        ELEMENT,
        [shipped(0, 5), shipped(0, 6, withdrawn=True), shipped(0, 7, withdrawn=True)],
        removed_in=(1, 0),
    )
    assert verdict.lifecycle is Lifecycle.COMPLIANT
    assert verdict.justified is True
    assert "marked in 0.6" in verdict.detail
    assert "removed in 1.0" in verdict.detail


def test_an_in_between_release_counts_while_the_element_still_ships():
    """The mark's job was done when it first appeared; presence is the bar."""
    verdict = lifecycle_verdict(
        ELEMENT,
        [shipped(0, 5), shipped(0, 6, withdrawn=True), shipped(0, 7)],
        removed_in=(1, 0),
    )
    assert verdict.lifecycle is Lifecycle.COMPLIANT


def test_order_of_the_record_does_not_matter():
    scrambled = [
        shipped(0, 7, withdrawn=True),
        shipped(0, 5),
        shipped(0, 6, withdrawn=True),
    ]
    assert lifecycle_verdict(ELEMENT, scrambled, removed_in=(1, 0)).lifecycle is (
        Lifecycle.COMPLIANT
    )


# --- what the record cannot settle --------------------------------------


def test_a_mark_at_the_oldest_known_release_is_undetermined():
    """The mark may have appeared earlier still; that is not ours to guess.

    The difference from the violation cases is one release: without an older,
    unmarked release, there is no evidence of *when* marking began.
    """
    verdict = lifecycle_verdict(
        ELEMENT, [shipped(0, 6, withdrawn=True)], removed_in=(1, 0)
    )
    assert verdict.lifecycle is Lifecycle.UNDETERMINED
    assert verdict.justified is False
    assert "as far back as the record goes" in verdict.detail


def test_an_empty_record_is_undetermined_not_a_pass():
    verdict = lifecycle_verdict(ELEMENT, [], removed_in=(1, 0))
    assert verdict.lifecycle is Lifecycle.UNDETERMINED
    assert verdict.justified is False


def test_undetermined_is_never_justified():
    """The one property the whole design rests on, asserted on its own."""
    for history in ([], [shipped(0, 6, withdrawn=True)]):
        assert lifecycle_verdict(ELEMENT, history, removed_in=(1, 0)).justified is False


# --- a mark that names nowhere to go ------------------------------------


def test_a_notice_naming_another_path_states_a_replacement():
    assert states_replacement(
        "spoc.scaffold.extract_archive is deprecated; import it from "
        "spoc.scaffold.archive instead. The re-export is removed at 1.0.",
        ELEMENT,
    )


def test_a_notice_naming_only_the_element_itself_states_nothing():
    """Every notice names the element. That alone is not a replacement."""
    assert not states_replacement(
        "spoc.scaffold.extract_archive is deprecated and goes away at 1.0.", ELEMENT
    )


def test_a_notice_saying_there_is_no_replacement_is_complete():
    assert states_replacement(
        "spoc.scaffold.extract_archive is deprecated with no replacement.", ELEMENT
    )


def test_a_version_number_is_not_a_replacement_path():
    assert not states_replacement("deprecated; removed at 1.0.", ELEMENT)


def test_an_incomplete_notice_is_reported_against_its_element():
    _, findings = derive_contract(
        [withdrawn_exposure("deprecated.", replacement_stated=False)]
    )
    assert [f.kind for f in findings] == [Kind.UNREPLACED]
    assert findings[0].fatal is True


def test_a_complete_notice_is_not_reported():
    _, findings = derive_contract(
        [withdrawn_exposure("use spoc.scaffold.archive", replacement_stated=True)]
    )
    assert findings == []


def test_a_marked_element_keeps_its_tier():
    """Withdrawal sits beside the tier. It never replaces it."""
    contract, _ = derive_contract(
        [withdrawn_exposure("use spoc.scaffold.archive", replacement_stated=True)]
    )
    assert ELEMENT in contract.public
