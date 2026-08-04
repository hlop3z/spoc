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
from pathlib import Path


def inject_apps(
    base_dir: Path, apps_dir_name: str = "apps", *, position: int = 0
) -> Path:
    """Ensure ``<base_dir>/apps`` exists and is importable, and return it."""
    apps_path = base_dir / apps_dir_name
    apps_path.mkdir(parents=True, exist_ok=True)
    if str(apps_path) not in sys.path:
        sys.path.insert(position, str(apps_path))
    return apps_path
