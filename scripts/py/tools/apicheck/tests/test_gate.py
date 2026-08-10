"""What the gate does with a lifecycle verdict, and when it starts caring.

Every rule here is reported from the day it lands but only fatal from 1.0, so
the path from "reported" to "enforced" would otherwise go unexercised until the
release it exists to protect. These drive it directly by writing a declared
version into a synthetic repository, which is the whole point: the first time
this fires for real must not be the first time it has ever run.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from apicheck.diffcli import main

PRESENT = '''
def thing():
    """A thing."""


__all__ = ["thing"]
'''

MARKED = """
from spoc.core.deprecation import deprecated_alias
from . import later

thing = deprecated_alias(
    later.thing, "spoc.thing is deprecated; use spoc.later.thing instead."
)

__all__ = ["thing"]
"""

REMOVED = """
__all__ = []
"""


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def project(tmp_path):
    """A repository whose `spoc` package is rewritten and tagged per release."""

    def build(releases: list[tuple[str, str]], working: str, version: str) -> Path:
        git(tmp_path, "init", "-q")
        git(tmp_path, "config", "user.email", "t@example.com")
        git(tmp_path, "config", "user.name", "t")
        pkg = tmp_path / "src" / "spoc"
        pkg.mkdir(parents=True)
        (pkg / "later.py").write_text(
            'def thing():\n    """The real one."""\n', encoding="utf-8"
        )

        for tag, body in releases:
            (pkg / "__init__.py").write_text(body, encoding="utf-8")
            (pkg / "__about__.py").write_text(
                f'__version__ = "{tag.lstrip("v")}"\n', encoding="utf-8"
            )
            git(tmp_path, "add", ".")
            git(tmp_path, "commit", "-qm", tag)
            git(tmp_path, "tag", tag)

        # The working tree is what is being judged; it is deliberately not
        # committed, exactly as a real pre-release working tree is not.
        (pkg / "__init__.py").write_text(working, encoding="utf-8")
        (pkg / "__about__.py").write_text(
            f'__version__ = "{version}"\n', encoding="utf-8"
        )
        return tmp_path

    return build


# --- before 1.0: reported, never enforced -------------------------------


def test_an_undeprecated_removal_is_reported_but_passes_before_1_0(project, capsys):
    """The pre-stable allowance permits exactly this. Failing would make the
    gate contradict the policy it enforces."""
    repo = project([("v0.5.0", PRESENT), ("v0.6.0", PRESENT)], REMOVED, "0.7.0")

    assert main(repo) == 0
    out = capsys.readouterr()
    assert "violated: spoc.thing" in out.out
    assert "pre-1.0: reported, not enforced" in out.err


# --- from 1.0: the allowance is spent -----------------------------------


def test_an_undeprecated_removal_fails_from_1_0(project, capsys):
    repo = project([("v0.5.0", PRESENT), ("v0.6.0", PRESENT)], REMOVED, "1.0.0")

    assert main(repo) == 1
    assert "no published release carried a mark" in capsys.readouterr().out


def test_a_removal_one_minor_too_early_fails_from_1_0(project, capsys):
    """Marked in 0.6 and removed in 1.0 with nothing shipped in between."""
    repo = project([("v0.5.0", PRESENT), ("v0.6.0", MARKED)], REMOVED, "1.0.0")

    assert main(repo) == 1
    assert "no full minor release in between" in capsys.readouterr().out


def test_a_completed_lifecycle_passes_from_1_0(project, capsys):
    repo = project(
        [("v0.5.0", PRESENT), ("v0.6.0", MARKED), ("v0.7.0", MARKED)],
        REMOVED,
        "1.0.0",
    )

    assert main(repo) == 0
    assert "compliant: spoc.thing" in capsys.readouterr().out


def test_a_completed_lifecycle_still_fails_outside_a_major_release(project, capsys):
    """The lifecycle earns a removal; only a major release may make it.

    The complement of the test above, and the reason the increment rule is not
    a blanket pass: same compliant verdict, same removal, but claimed as a minor
    bump, so the incompatible change has no release to legitimately ship in.
    """
    repo = project(
        [("v1.0.0", PRESENT), ("v1.1.0", MARKED), ("v1.2.0", MARKED)],
        REMOVED,
        "1.3.0",
    )

    assert main(repo) == 1
    out = capsys.readouterr()
    assert "compliant: spoc.thing" in out.out
    assert "permitted" not in out.err


def test_an_undeterminable_history_exits_two_not_zero(project, capsys):
    """Marked as far back as the record goes. Not a pass, and not a verdict."""
    repo = project([("v0.6.0", MARKED)], REMOVED, "1.0.0")

    assert main(repo) == 2
    out = capsys.readouterr().out
    assert "undetermined: spoc.thing" in out
    assert "1 undetermined" in out


# --- what the run always says -------------------------------------------


def test_the_undetermined_count_appears_in_the_summary(project, capsys):
    """A run must never imply a check it did not perform."""
    repo = project([("v0.6.0", MARKED)], REMOVED, "1.0.0")
    main(repo)

    assert "0 incomplete withdrawal(s), 1 undetermined" in capsys.readouterr().out


def test_a_withdrawal_in_flight_is_reported_beside_its_tier(project, capsys):
    """Still exposed, still promising what it promised."""
    repo = project([("v0.5.0", PRESENT)], MARKED, "0.6.0")
    main(repo)

    assert "withdrawing: spoc.thing (still public)" in capsys.readouterr().out
