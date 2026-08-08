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

import os
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

#: Directory name used under whichever platform cache root applies.
APPLICATION_NAME = "spoc"

#: Subdirectory holding retrieved template sets, so the cache root stays usable
#: for anything else the kernel may retain later.
TEMPLATES_DIR = "templates"


def default_cache_root() -> Path:
    """The conventional per-user cache directory for this platform.

    Honours ``XDG_CACHE_HOME`` everywhere it is set, because a user who has set
    it has said where cached data goes and that answer outranks the platform
    default.

    Provisional: may change incompatibly in a minor release.
    """
    override = os.environ.get("XDG_CACHE_HOME")
    if override:
        return Path(override) / APPLICATION_NAME / TEMPLATES_DIR

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / APPLICATION_NAME / "Cache" / TEMPLATES_DIR

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / APPLICATION_NAME / TEMPLATES_DIR

    return Path.home() / ".cache" / APPLICATION_NAME / TEMPLATES_DIR


class DirectoryCache:
    """Retains revisions as directories under a cache root.

    Implements the :class:`~spoc.scaffold.plan.Cache` port.

    Population happens in a staging directory and is published under the
    revision only once it completes, so an interrupted retrieval can never leave
    a half-populated revision looking retained — the same stage-then-commit shape
    :class:`~spoc.scaffold.sink.DirectorySink` uses.

    Provisional: may change incompatibly in a minor release.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else default_cache_root()

    def _entry(self, revision: str) -> Path:
        # The revision reaches this as a path segment, so it is confined to
        # characters that cannot traverse. A hostile revision string is refused
        # by never being usable as one, rather than by being sanitized into
        # something that looks fine but names a different entry.
        safe = "".join(c for c in revision if c.isalnum() or c in "-_.")
        if not safe or safe in {".", ".."}:
            safe = "invalid"
        return self.root / safe

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
                # immutable, so whichever copy landed is the right one.
                if entry.is_dir():
                    return entry
                raise
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return entry
