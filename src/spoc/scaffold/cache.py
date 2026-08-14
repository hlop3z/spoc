"""
Retaining retrieved revisions so a repeat generation retrieves nothing.

Keyed by the exact revision, which is what makes this correct without any
invalidation logic: a revision is immutable, so content retained under one is
never stale for it. There is nothing to expire, only something to grow.

The platform conventions are read directly rather than through a library. That
is a deliberate, recorded choice: the conventions are the standard worth
adopting, and taking a dependency for fifteen lines of them would either break
the kernel's empty dependency set or push this feature behind an extra — which
would reinstate the two-step install the feature exists to remove.
"""

import hashlib
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path

#: The characters a revision may carry to be usable as a path segment at all.
#: Deliberately narrow: it admits the hexadecimal digests and tag-shaped names
#: revisions actually take, and nothing that carries a separator, a wildcard, or a
#: platform's reserved punctuation. Necessary but not sufficient — a store may still
#: fold two of these names together, which is what :func:`_is_held_faithfully` adds.
#: Anything outside it is named by its digest instead — never filtered into this
#: shape, which is what would let two revisions share one entry.
_SAFE_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")

#: Directory name used under whichever platform cache root applies.
APPLICATION_NAME = "spoc"

#: Subdirectory holding retrieved template sets, so the cache root stays usable
#: for anything else the kernel may retain later.
TEMPLATES_DIR = "templates"


def _is_held_faithfully(revision: str) -> bool:
    """Whether a store is guaranteed to hold this revision under the name given.

    Usable as a path segment is not the same as held under that name, and the
    difference is where two revisions come to share one entry. A store that folds
    case holds ``Rev`` and ``rev`` in one place; one that drops a trailing dot
    holds ``v1.`` and ``v1`` in one. Both are ordinary developer machines, so the
    test is made of what every declared platform holds unaltered, not of what the
    running one happens to: no uppercase letter, no trailing dot.

    ``.`` and ``..`` are named as well as excluded by the trailing dot, so
    relaxing one rule later cannot quietly reintroduce a traversal.
    """
    return bool(
        _SAFE_SEGMENT.fullmatch(revision)
        and revision not in {".", ".."}
        and not revision.endswith(".")
        and revision == revision.lower()
    )


def cache_root_for(platform: str, environ: Mapping[str, str], home: Path) -> Path:
    """The conventional per-user cache directory, for a platform named as a value.

    The platform is an argument rather than a read of :data:`sys.platform` so that
    every branch is reachable from every host. A contributor on one platform is
    otherwise blind to the other two, and a coverage figure measured on Windows
    reports the POSIX arms dark while the same suite on Linux reports the Windows
    arm dark — the number becomes a property of the machine instead of the code.

    Honours ``XDG_CACHE_HOME`` on every platform, not only where it is native,
    because a user who has set it has said where cached data goes and that answer
    outranks the platform default.
    """
    override = environ.get("XDG_CACHE_HOME")
    if override:
        return Path(override) / APPLICATION_NAME / TEMPLATES_DIR

    if platform == "win32":
        base = environ.get("LOCALAPPDATA") or environ.get("APPDATA")
        root = Path(base) if base else home / "AppData" / "Local"
        return root / APPLICATION_NAME / "Cache" / TEMPLATES_DIR

    if platform == "darwin":
        return home / "Library" / "Caches" / APPLICATION_NAME / TEMPLATES_DIR

    return home / ".cache" / APPLICATION_NAME / TEMPLATES_DIR


def default_cache_root() -> Path:
    """The conventional per-user cache directory for the running platform.

    The adapter over :func:`cache_root_for`: it reads the ambient platform, the
    environment, and the home directory, and holds no logic of its own.
    """
    return cache_root_for(sys.platform, os.environ, Path.home())


class DirectoryCache:
    """Retains revisions as directories under a cache root.

    Implements the :class:`~spoc.scaffold.plan.Cache` port.

    Population happens in a staging directory and is published under the
    revision only once it completes, so an interrupted retrieval can never leave
    a half-populated revision looking retained — the same stage-then-commit shape
    :class:`~spoc.scaffold.sink.DirectorySink` uses.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else default_cache_root()

    def _entry(self, revision: str) -> Path:
        """The location holding this revision, and no other revision's content.

        The revision reaches this as a path segment, so it must be confined to
        characters that cannot traverse. Filtering it to those characters is the
        obvious move and is wrong: filtering is lossy, so ``feature/x`` and
        ``featurex`` both land here as ``featurex`` and one revision is served
        the other's content — the single thing a cache keyed by an immutable
        revision must never do.

        So the mapping is total instead. A revision the store holds under the
        name given (:func:`_is_held_faithfully`) is used verbatim, which covers
        the commit digests and tag shapes references resolve to; every other
        revision is named by its digest. Distinct revisions therefore keep
        distinct entries — distinct as the store judges it, not merely as the
        strings differ, which is the stronger claim this has to make.

        A revision that was retained verbatim under a name the store does not
        hold faithfully — a mixed-case tag, or one ending in a dot — is retained
        again under its digest, once. A cache miss costs a retrieval; the
        collision it replaces cost correctness.

        An empty revision cannot arrive here through a load — `RemoteTemplateSource`
        refuses it where the reference is still known, which makes for a message the
        caller can act on — so this maps it like anything else rather than restating
        that refusal in a place with less to say.
        """
        if _is_held_faithfully(revision):
            return self.root / revision
        digest = hashlib.sha256(revision.encode("utf-8")).hexdigest()
        return self.root / f"rev-{digest[:32]}"

    def retained(self, revision: str) -> Path | None:
        entry = self._entry(revision)
        return entry if entry.is_dir() else None

    def retain(self, revision: str, populate: Callable[[Path], None]) -> Path:
        entry = self._entry(revision)
        if entry.is_dir():
            return entry

        entry.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=entry.parent))
        try:
            populate(staging)
            try:
                staging.replace(entry)
            except OSError:
                # Another process may have published the same revision first.
                # That is a race with a correct outcome: the revision is
                # immutable, so whichever copy landed is the right one. If it
                # did not land, the failure is real and must surface.
                if not entry.is_dir():
                    raise
                # Losing the race leaves our staged copy redundant. It has to be
                # removed here and not by the handler below, which only runs when
                # this raises — nothing expires from this cache, so a directory
                # left once is left for good.
                shutil.rmtree(staging, ignore_errors=True)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return entry
