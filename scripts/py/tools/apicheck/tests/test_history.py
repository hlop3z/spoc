"""Walking the published releases to find when a mark first appeared.

These build a real repository and tag it, because the thing under test is the
adapter that reads git — a fake would only prove the fake agrees with itself.
Each release commits a whole tiny package, so the ordinary extractor reads every
side of the comparison exactly as it reads the working tree.

The patch-release case is the one with teeth: three tags in one minor line are
one release as far as the waiting period is concerned, and a walk that counted
tags would wave the removal through.
"""

from __future__ import annotations

import subprocess

import pytest
from apicheck.core import Lifecycle, lifecycle_verdict
from apicheck.release import minor_line, released_tags, withdrawal_history
from packaging.version import Version

ELEMENT = "pkg.thing"

PLAIN = '''
def thing():
    """A thing."""


__all__ = ["thing"]
'''

MARKED = """
from spoc.core.deprecation import deprecated_alias
from . import later


thing = deprecated_alias(
    later.thing, "pkg.thing is deprecated; use pkg.later.thing instead."
)

__all__ = ["thing"]
"""

GONE = """
__all__ = []
"""


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def releases(tmp_path):
    """Commit a sequence of `(tag, package body)` pairs, tagging each."""

    def build(sequence: list[tuple[str, str]]):
        git(tmp_path, "init", "-q")
        git(tmp_path, "config", "user.email", "t@example.com")
        git(tmp_path, "config", "user.name", "t")
        pkg = tmp_path / "src" / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "later.py").write_text(
            'def thing():\n    """The real one."""\n', encoding="utf-8"
        )

        for tag, body in sequence:
            (pkg / "__init__.py").write_text(body, encoding="utf-8")
            # Two consecutive releases may expose exactly the same surface —
            # that is the normal case, not an edge one — and git refuses an
            # empty commit. This gives every release something of its own to
            # carry without touching the package the extractor reads.
            (tmp_path / "RELEASE").write_text(tag, encoding="utf-8")
            git(tmp_path, "add", ".")
            git(tmp_path, "commit", "-qm", tag)
            git(tmp_path, "tag", tag)
        return tmp_path

    return build


def history(repo, before=(1, 0)):
    return withdrawal_history(repo, ELEMENT, before=before, package="pkg")


# --- ordering and the unit of counting ----------------------------------


def test_tags_are_ordered_by_version_not_creation_date(releases):
    """v0.10.0 is newer than v0.9.0. Sorted as text it is not."""
    repo = releases([("v0.9.0", PLAIN), ("v0.10.0", PLAIN)])
    assert [tag for _, tag in released_tags(repo)] == ["v0.10.0", "v0.9.0"]


def test_a_tag_that_is_not_a_version_is_skipped(releases):
    repo = releases([("v0.9.0", PLAIN)])
    git(repo, "tag", "nightly")
    assert [tag for _, tag in released_tags(repo)] == ["v0.9.0"]


def test_a_version_reduces_to_its_minor_line():
    assert minor_line(Version("0.6.3")) == (0, 6)
    assert minor_line(Version("1.0.0rc1")) == (1, 0)


# --- what the walk records ----------------------------------------------


def test_the_release_that_marked_it_is_found(releases):
    repo = releases(
        [("v0.5.0", PLAIN), ("v0.6.0", MARKED), ("v0.7.0", MARKED)],
    )
    record = history(repo)

    assert lifecycle_verdict(ELEMENT, record, removed_in=(1, 0)).lifecycle is (
        Lifecycle.COMPLIANT
    )


def test_patch_releases_in_one_minor_line_do_not_satisfy_the_wait(releases):
    """0.6.0, 0.6.1 and 0.6.2 all carry the mark. That is one release."""
    repo = releases(
        [
            ("v0.5.0", PLAIN),
            ("v0.6.0", MARKED),
            ("v0.6.1", MARKED),
            ("v0.6.2", MARKED),
        ],
    )
    record = history(repo)

    assert {presence.line for presence in record} == {(0, 5), (0, 6)}
    assert lifecycle_verdict(ELEMENT, record, removed_in=(1, 0)).lifecycle is (
        Lifecycle.VIOLATED
    )


def test_a_removal_that_was_never_marked_is_caught(releases):
    repo = releases([("v0.5.0", PLAIN), ("v0.6.0", PLAIN), ("v0.7.0", PLAIN)])
    assert lifecycle_verdict(ELEMENT, history(repo), removed_in=(1, 0)).lifecycle is (
        Lifecycle.VIOLATED
    )


def test_the_walk_stops_at_the_first_unmarked_release(releases):
    """Everything older is settled once an unmarked release is reached."""
    repo = releases(
        [
            ("v0.1.0", PLAIN),
            ("v0.2.0", PLAIN),
            ("v0.3.0", PLAIN),
            ("v0.6.0", MARKED),
            ("v0.7.0", MARKED),
        ],
    )
    record = history(repo)

    assert [presence.line for presence in record] == [(0, 7), (0, 6), (0, 3)]


def test_releases_at_or_after_the_removal_are_not_consulted(releases):
    repo = releases([("v0.5.0", PLAIN), ("v0.6.0", MARKED)])
    assert history(repo, before=(0, 6)) == history(repo, before=(0, 6))
    assert all(presence.line < (0, 6) for presence in history(repo, before=(0, 6)))


# --- what it cannot settle ----------------------------------------------


def test_a_repository_with_no_tags_yields_an_empty_record(releases):
    repo = releases([])
    (repo / "src" / "pkg" / "__init__.py").write_text(PLAIN, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "untagged")

    record = history(repo)
    assert record == []
    assert lifecycle_verdict(ELEMENT, record, removed_in=(1, 0)).lifecycle is (
        Lifecycle.UNDETERMINED
    )


def test_a_mark_present_at_the_oldest_tag_is_undetermined(releases):
    """No older, unmarked release means no evidence of when marking began."""
    repo = releases([("v0.6.0", MARKED)])
    verdict = lifecycle_verdict(ELEMENT, history(repo), removed_in=(1, 0))

    assert verdict.lifecycle is Lifecycle.UNDETERMINED
    assert verdict.justified is False


def test_an_element_absent_from_the_record_is_recorded_absent(releases):
    repo = releases([("v0.5.0", GONE), ("v0.6.0", MARKED)])
    record = history(repo)

    assert any(presence.present is False for presence in record)
