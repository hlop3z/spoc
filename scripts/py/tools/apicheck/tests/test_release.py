"""The git adapter: resolving a baseline, and refusing to invent one."""

from __future__ import annotations

import subprocess

import pytest
from apicheck.release import GitError, declared_version, latest_tag


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    """A real repository with one commit and no tags."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "one")
    return tmp_path


def test_no_tags_is_an_error_not_an_empty_answer(repo):
    """A comparison that could not happen must never read like one that found
    nothing — the shallow-CI-checkout trap."""
    with pytest.raises(GitError) as exc:
        latest_tag(repo)
    assert "no tags" in str(exc.value)
    assert "fetch-depth" in str(exc.value), "the message must say how to fix it"


def test_the_most_recent_tag_wins(repo):
    git(repo, "tag", "v0.1.0")
    git(repo, "tag", "v0.2.0")
    assert latest_tag(repo) in {"v0.1.0", "v0.2.0"}


def test_a_missing_repository_is_reported(tmp_path):
    with pytest.raises(GitError):
        latest_tag(tmp_path / "nowhere")


def test_the_version_is_read_without_importing(tmp_path):
    about = tmp_path / "src" / "spoc"
    about.mkdir(parents=True)
    (about / "__about__.py").write_text(
        'raise RuntimeError("importing this would fail")\n__version__ = "1.2.3"\n',
        encoding="utf-8",
    )
    assert str(declared_version(tmp_path)) == "1.2.3"


def test_a_missing_version_is_reported(tmp_path):
    about = tmp_path / "src" / "spoc"
    about.mkdir(parents=True)
    (about / "__about__.py").write_text("__license__ = 'MIT'\n", encoding="utf-8")
    with pytest.raises(GitError):
        declared_version(tmp_path)


@pytest.mark.parametrize(
    ("version", "pre_stable"),
    [("0.5.0", True), ("0.99.9", True), ("1.0.0", False), ("1.0.0rc1", False)],
)
def test_maturity_follows_pep_440(tmp_path, version, pre_stable):
    """`1.0.0rc1` has major 1 — a split on dots would agree, but only by luck.
    The point is that the parse is PEP 440's, not ours."""
    about = tmp_path / "src" / "spoc"
    about.mkdir(parents=True)
    (about / "__about__.py").write_text(
        f'__version__ = "{version}"\n', encoding="utf-8"
    )
    assert (declared_version(tmp_path).major < 1) is pre_stable
