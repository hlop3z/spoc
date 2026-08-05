"""
Making a project's ``apps`` directory importable.

Apps are imported by their bare package name (``blog.models``, not
``myproject.apps.blog.models``), which keeps the namespace segment of every identifier
equal to the app's own name. That only works if the ``apps`` directory is itself on the
import path, so this is the one place the kernel mutates process-global state — done once,
explicitly, from ``start``.
"""

from __future__ import annotations

import sys
from contextlib import suppress
from pathlib import Path


def inject_apps(
    base_dir: Path, apps_dir_name: str = "apps", *, position: int = 0
) -> tuple[Path, bool]:
    """Ensure ``<base_dir>/apps`` exists and is importable.

    Returns the path and whether *this call* put it on ``sys.path``. The flag is
    the ownership token :func:`eject_apps` needs: an entry that was already there
    belongs to whoever added it, and removing it on our way out would break them.
    """
    apps_path = base_dir / apps_dir_name
    apps_path.mkdir(parents=True, exist_ok=True)
    entry = str(apps_path)
    if entry in sys.path:
        return apps_path, False
    sys.path.insert(position, entry)
    return apps_path, True


def eject_apps(base_dir: Path, apps_dir_name: str = "apps") -> None:
    """Undo :func:`inject_apps`: drop ``<base_dir>/apps`` from the import path.

    Only for the caller that :func:`inject_apps` reported an insertion to. Calling
    it otherwise strips an entry this process does not own.
    """
    with suppress(ValueError):
        sys.path.remove(str(base_dir / apps_dir_name))
