# -*- coding: utf-8 -*-
"""
inject_apps.py

Provides utilities for injecting the `apps` directory into the Python path.

Tested on Python 3.13+.
"""

import sys
from pathlib import Path


def ensure_directory(path: Path, *, exist_ok: bool = True) -> None:
    """
    Ensure that the given directory exists.
    """
    try:
        path.mkdir(parents=True, exist_ok=exist_ok)
    except Exception as e:
        raise e


def add_to_python_path(path: Path, position: int = 0) -> None:
    """
    Insert the given path into sys.path if not already present.
    """
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(position, str_path)


def inject_apps(
    base_dir: Path, apps_dir_name: str = "apps", *, position: int = 0
) -> Path:
    """
    Ensure an 'apps' directory exists under `base_dir` and inject it into Python's import path.
    """
    apps_path = base_dir / apps_dir_name
    print("apps_path", apps_path)
    ensure_directory(apps_path)
    add_to_python_path(apps_path, position=position)
    return apps_path
