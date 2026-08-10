"""Adapter: the previously released surface, read out of git.

The comparison has to classify both sides with the *same* rules, or an element
could be reported as added at one tier while actually carrying another. So this
does not ask griffe to load a ref directly — it materializes the ref's `src/`
into a temporary directory and hands that to the ordinary extractor, which is
then doing exactly what it does for the working tree.

`git archive` rather than a worktree or a clone: it writes nothing into the
repository, needs no lock, and cannot disturb a working tree someone is using.
"""

from __future__ import annotations

import ast
import io
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from packaging.version import InvalidVersion, Version

from apicheck import extract
from apicheck.core import Exposure, MinorLine, ReleasePresence


class GitError(RuntimeError):
    """Git could not answer — a missing ref, a shallow clone, or no repository."""


def _git(repo: Path, *args: str) -> str:
    """Run a git plumbing command, raising `GitError` with git's own complaint."""
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - git absent
        raise GitError("git is not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise GitError(f"git {' '.join(args)}: {detail}") from exc
    return done.stdout


def latest_tag(repo: Path) -> str:
    """The most recent reachable tag.

    Raises rather than returning `None` when there is none. A baseline that
    could not be resolved must never be reported the same way as a baseline
    with nothing to report — a shallow CI checkout has no tags, and silently
    treating that as "no changes" would pass the gate while checking nothing.
    """
    tags = _git(repo, "tag", "--list", "--sort=-creatordate").split()
    if not tags:
        raise GitError(
            "no tags in this repository, so there is no released baseline to "
            "compare against. In CI this usually means a shallow checkout: "
            "fetch tags (actions/checkout with fetch-depth: 0)."
        )
    return tags[0]


@contextmanager
def source_at(repo: Path, ref: str) -> Iterator[Path]:
    """The ref's `src/` materialized in a temporary directory.

    Yielded as a path rather than a loaded model so both readers — the tier
    extractor and the breakage differ — see the same bytes on disk, and neither
    has to know how the other gets there.
    """
    archive = _git_bytes(repo, "archive", ref, "src")

    with tempfile.TemporaryDirectory(prefix="apidiff-") as tmp:
        root = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            # `git archive` output is produced by git from its own object store,
            # not supplied by a third party, so the contents are already trusted
            # in the way the scaffolder's archive admission is not. `data` is
            # still the right filter: it refuses absolute paths and traversal
            # without needing a reason to expect them.
            tar.extractall(root, filter="data")
        yield root / "src"


def surface_at(repo: Path, ref: str, package: str = "spoc") -> list[Exposure]:
    """The exposures of `package` as of `ref`, read through the usual extractor."""
    with source_at(repo, ref) as src:
        return extract.exposures(src, package)


def released_tags(repo: Path) -> list[tuple[Version, str]]:
    """Every tag that parses as a version, newest first.

    Ordered by parsed version rather than creation date. `latest_tag` sorts by
    date because "the last release cut" is a question about time; this asks
    which releases came before which, and a retagged or back-dated release must
    not be able to reorder that. The two orderings are kept apart on purpose.

    A tag that is not a version is skipped rather than guessed at.
    """
    versions = []
    for tag in _git(repo, "tag", "--list").split():
        try:
            versions.append((Version(tag.lstrip("v")), tag))
        except InvalidVersion:
            continue
    return sorted(versions, reverse=True)


def tag_version(ref: str) -> Version | None:
    """The version a ref names, or `None` when it is not a released tag.

    `None` is the honest answer for a branch or a commit hash, and the caller
    must treat it as "the increment cannot be established" rather than as any
    particular increment — guessing here would decide whether a breaking change
    is permitted.
    """
    try:
        return Version(ref.lstrip("v"))
    except InvalidVersion:
        return None


def minor_line(version: Version) -> MinorLine:
    """A version reduced to the line the waiting period is counted in.

    Everything after the minor is discarded, which is what stops a patch release
    from satisfying a period the policy measures in minor releases.
    """
    return (version.major, version.minor)


def withdrawal_history(
    repo: Path, element: str, before: MinorLine, package: str = "spoc"
) -> list[ReleasePresence]:
    """How the published releases behind `before` exposed one element.

    Walked newest-first and stopped early: once a release is reached that does
    not carry the mark — because the element is there unmarked, or is not there
    at all — everything older is settled. The mark began after that release, and
    no earlier tag can change the verdict. So a removal costs a few extractions
    rather than one per tag, and a run with no promised removals never calls
    this at all.

    Returns as much as could be read. An empty result means nothing was
    readable, which the verdict treats as undetermined rather than as innocent.
    """
    history: list[ReleasePresence] = []

    for version, tag in released_tags(repo):
        line = minor_line(version)
        if line >= before:
            continue

        try:
            exposures = surface_at(repo, tag, package)
        except GitError:
            # One unreadable ref is a gap in the record, not a reason to
            # abandon the rest of it. An empty record is what says "nothing
            # could be read", and that is already reported as undetermined.
            continue

        found = next((e for e in exposures if e.element == element), None)
        history.append(
            ReleasePresence(
                line=line,
                present=found is not None,
                withdrawn=found is not None and found.withdrawal is not None,
            )
        )

        if found is None or found.withdrawal is None:
            break

    return history


def declared_version(repo: Path, package: str = "spoc") -> Version:
    """The version in `__about__.py`, read without importing the package.

    `pyproject.toml` declares the version dynamic, so the source file is the
    only place it is actually written.
    """
    about = repo / "src" / package / "__about__.py"
    try:
        tree = ast.parse(about.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GitError(f"{about}: cannot read the declared version") from exc

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Name)
                and target.id == "__version__"
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                return Version(node.value.value)

    raise GitError(f"{about}: no __version__ assignment found")


def _git_bytes(repo: Path, *args: str) -> bytes:
    """`_git`, for a command whose output is binary."""
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, check=True
        )
    except FileNotFoundError as exc:  # pragma: no cover - git absent
        raise GitError("git is not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode(errors="replace").strip()
        raise GitError(f"git {' '.join(args)}: {detail}") from exc
    return done.stdout
