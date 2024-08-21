# -*- coding: utf-8 -*-
"""
Collect & Inject

This module provides functionality for collecting and injecting
`apps`, `modules`, `settings`, and `configuration` files (e.g., TOML files).

"""

import os
import pathlib
import sys
from typing import Any

from .importer import frozendict
from .importer.base import search_method
from .toml_core import TOML

DEFAULT_MODE = "development"


def inject_apps_folder(base_dir: pathlib.Path) -> Any:
    """Inject { ./apps } Directory"""

    base_apps = pathlib.Path(base_dir / "apps")
    base_apps.mkdir(parents=True, exist_ok=True)
    if base_apps.exists():
        sys.path.insert(0, os.path.join(base_dir, "apps"))


def collect_apps_partial(app_mode: str, the_apps: dict) -> Any:
    """Collect All Apps"""
    installed_apps = []
    match app_mode:
        case "production":
            installed_apps.extend(the_apps.get("production", []))
        case "staging":  # production + staging
            installed_apps.extend(the_apps.get("production", []))
            installed_apps.extend(the_apps.get("staging", []))
        case "development":  # production + staging + development
            installed_apps.extend(the_apps.get("production", []))
            installed_apps.extend(the_apps.get("staging", []))
            installed_apps.extend(the_apps.get("development", []))
    return installed_apps


def collect_installed_apps(toml_dir, settings: Any = None) -> Any:
    """Collect All Apps"""

    # Step[1]: INIT { Values }
    toml_spoc = toml_dir["spoc"].get("spoc", {})
    the_apps = toml_spoc.get("apps", {})
    app_mode = toml_spoc.get("mode", DEFAULT_MODE)

    # Installed Apps
    installed_apps = []

    # Step[2]: Collect `settings` Apps
    if hasattr(settings, "INSTALLED_APPS"):
        installed_apps.extend(settings.INSTALLED_APPS)

    # Step[3]: Collect `toml` Apps
    installed_apps.extend(collect_apps_partial(app_mode, the_apps))

    return list(set(installed_apps))


def get_toml_file(toml_file: pathlib.Path) -> Any:
    """Get { TOML } File"""

    # Load File
    manager = TOML(toml_file)

    # Loaded or Blank dict
    if toml_file.exists():
        return frozendict(**manager.read())
    return frozendict({})


def get_toml_files(base_dir: pathlib.Path) -> dict:
    """Collect All { TOML } Files"""

    return {
        "spoc": get_toml_file(base_dir / "config" / "spoc.toml"),
        "pyproject": get_toml_file(base_dir / "pyproject.toml"),
    }


def get_app_mode(toml_dir) -> Any:
    """Get App { Mode }"""
    return toml_dir["spoc"].get("mode", DEFAULT_MODE)


def collect_extras(extras, settings) -> Any:
    """Collect All Extra { Python-Objects }"""
    all_extras_modules: dict = {}

    # Get From Settings
    settings_extras: dict = {}
    if hasattr(settings, "EXTRAS") and isinstance(settings.EXTRAS, dict):
        settings_extras = settings.EXTRAS

    # Internal Util
    def collector(extra_dict):
        for group, items in extra_dict.items():
            if group not in all_extras_modules:
                all_extras_modules[group] = []
            for object_uri in items:
                obj = search_method(object_uri)
                if obj and obj not in all_extras_modules[group]:
                    all_extras_modules[group].append(obj)

    # Settings
    collector(settings_extras)

    # Toml
    collector(extras)

    # Finally
    return frozendict(all_extras_modules)


def load_envs(base_dir, mode) -> Any:
    """Load Environment Variables"""
    file_path: Any = base_dir / "config" / ".env" / f"{ mode }.toml"
    return frozendict(get_toml_file(file_path).get("env"))
