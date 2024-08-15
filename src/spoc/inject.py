# -*- coding: utf-8 -*-
"""[ Collect & Inject ]
Project (Module)
"""

import os
import pathlib
import sys
from typing import Any

from .importer import frozendict
from .importer.base import search_method
from .toml_core import TOML


def inject_apps_folder(base_dir: pathlib.Path):
    """Inject { ./apps } Directory"""

    base_apps = pathlib.Path(base_dir / "apps")
    base_apps.mkdir(parents=True, exist_ok=True)
    if base_apps.exists():
        sys.path.insert(0, os.path.join(base_dir, "apps"))


def collect_apps_partial(app_mode: str, the_apps: dict):
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


def collect_installed_apps(toml_dir, settings: Any = None):
    """Collect All Apps"""

    # Step[1]: INIT { Values }
    toml_spoc = toml_dir["spoc"].get("spoc", {})
    the_apps = toml_spoc.get("apps", {})
    app_mode = toml_spoc.get("mode", "development")

    # Installed Apps
    installed_apps = []

    # Step[2]: Collect Apps
    installed_apps.extend(collect_apps_partial(app_mode, the_apps))
    if hasattr(settings, "INSTALLED_APPS"):
        installed_apps.extend(settings.INSTALLED_APPS)

    return list(set(installed_apps))


def get_toml_file(toml_file: pathlib.Path):
    """Get { TOML } File"""

    manager = TOML(toml_file)

    if toml_file.exists():
        toml_dict = frozendict(**manager.read())
    else:
        toml_dict = frozendict({})
    return toml_dict


def get_toml_files(base_dir: pathlib.Path):
    """Collect All { TOML } Files"""

    return {
        "spoc": get_toml_file(base_dir / "config" / "spoc.toml"),
        "pyproject": get_toml_file(base_dir / "pyproject.toml"),
    }


def get_app_mode(toml_dir):
    """Get App { Mode }"""
    return toml_dir["spoc"].get("mode", "development")


def collect_extras(extras):
    """Collect All Extra { Python-Objects }"""

    all_extras_modules = {}
    for group, items in extras.items():
        all_extras_modules[group] = []
        for object_uri in items:
            obj = search_method(object_uri)
            if obj:
                all_extras_modules[group].append(obj)
    return frozendict(all_extras_modules)


def load_envs(base_dir, mode):
    """Load Environment Variables"""
    file_path = base_dir / "config" / ".env" / f"{ mode }.toml"
    return get_toml_file(file_path).get("env", {})
