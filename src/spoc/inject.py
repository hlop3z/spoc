# -*- coding: utf-8 -*-
"""
Collect & Inject

This module provides functionality for collecting and injecting
`apps`, `modules`, `settings`, and `configuration` files (e.g., TOML files).

"""

import pathlib
import sys
from typing import Any

from .importer import frozendict
from .importer.base import search_object
from .toml_core import TOML

DEFAULT_MODE = "development"


def inject_apps_folder(base_dir: pathlib.Path) -> None:
    """Inject the apps directory into the Python path.

    Creates an `apps` directory inside the given `base_dir` if it does not exist,
    and adds it to the Python system path to allow for module imports.

    Args:
        base_dir (pathlib.Path): The base directory where the `apps` folder will be injected.
    """
    base_apps = base_dir / "apps"
    base_apps.mkdir(parents=True, exist_ok=True)

    if base_apps.exists():
        sys.path.insert(0, str(base_apps))
        # sys.path.insert(0, os.path.join(base_dir, "apps"))


def collect_apps_partial(app_mode: str, the_apps: dict) -> list:
    """Collect apps based on the specified mode.

    Collects and returns a list of installed apps according to the given application mode.

    Args:
        app_mode (str): The current application mode (e.g., "production", "staging", "development").
        the_apps (dict): A dictionary of apps categorized by different modes.

    Returns:
        list: A list of installed apps corresponding to the specified mode.
    """
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


def collect_installed_apps(toml_dir: dict, settings: Any = None) -> list:
    """Collect all installed apps from settings and TOML configuration.

    Combines the apps listed in the settings and the TOML configuration files.

    Args:
        toml_dir (dict): A dictionary containing parsed TOML configuration files.
        settings (Any, optional): Settings object containing the `INSTALLED_APPS` attribute.

    Returns:
        list: A list of all unique installed apps.
    """
    toml_spoc = toml_dir.get("spoc", {}).get("spoc", {})
    the_apps = toml_spoc.get("apps", {})
    app_mode = toml_spoc.get("mode", DEFAULT_MODE)

    installed_apps = []

    if hasattr(settings, "INSTALLED_APPS"):
        installed_apps.extend(settings.INSTALLED_APPS)

    installed_apps.extend(collect_apps_partial(app_mode, the_apps))

    return list(set(installed_apps))


def get_toml_file(toml_file: pathlib.Path) -> frozendict:
    """Load a TOML file into a frozendict.

    Reads and parses a TOML file into a `frozendict` object.

    Args:
        toml_file (pathlib.Path): The path to the TOML file.

    Returns:
        frozendict: A frozendict containing the parsed TOML file data,
            or an empty frozendict if the file does not exist.
    """
    manager = TOML(toml_file)

    if toml_file.exists():
        return frozendict(**manager.read())
    return frozendict({})


def get_toml_files(base_dir: pathlib.Path) -> dict:
    """Collect all relevant TOML files.

    Gathers and returns a dictionary containing paths to essential TOML files for the application.

    Args:
        base_dir (pathlib.Path): The base directory where the configuration files are located.

    Returns:
        dict: A dictionary with keys 'spoc' and 'pyproject' pointing to their respective TOML files.
    """
    return {
        "spoc": get_toml_file(base_dir / "config" / "spoc.toml"),
        "pyproject": get_toml_file(base_dir / "pyproject.toml"),
    }


def get_app_mode(toml_dir: dict) -> str:
    """Get the current application mode.

    Retrieves the application mode from the TOML configuration.

    Args:
        toml_dir (dict): A dictionary containing parsed TOML configuration files.

    Returns:
        str: The current application mode (e.g., "development", "production").
    """
    return toml_dir.get("spoc", {}).get("mode", DEFAULT_MODE)


def collect_extra_plugins(extras: dict, settings: Any) -> frozendict:
    """Collect all extra Python objects (plugins).

    Gathers extra Python objects (such as plugins) from both settings and TOML configurations.

    Args:
        extras (dict): A dictionary containing extra plugins from the TOML configuration.
        settings (Any): Settings object that may contain a `PLUGINS` attribute.

    Returns:
        frozendict: A frozendict containing all collected extra plugins organized by group.
    """
    all_extras_modules: dict = {}

    settings_extras = (
        getattr(settings, "PLUGINS", {})
        if isinstance(getattr(settings, "PLUGINS", {}), dict)
        else {}
    )

    def collector(extra_dict: dict):
        """
        Helper function to collect objects from a dictionary of extras.
        """
        for group, items in extra_dict.items():
            if group not in all_extras_modules:
                all_extras_modules[group] = []
            for object_uri in items:
                obj = search_object(object_uri)
                if obj and obj not in all_extras_modules[group]:
                    all_extras_modules[group].append(obj)

    # Collectors
    collector(settings_extras)
    collector(extras)

    return frozendict(all_extras_modules)


def load_envs(base_dir: pathlib.Path, mode: str) -> frozendict:
    """Load environment variables from a TOML file based on the given mode.

    This function loads environment variables from a TOML file located in the
    `{base_dir}/config/.env/` directory. The specific file loaded depends on the
    provided `mode` (e.g., `development.toml`, `production.toml`).

    Args:
        base_dir (pathlib.Path): The base directory where configuration files are located.
        mode (str): The current application mode (e.g., "development", "production").

    Returns:
        frozendict: A frozendict containing environment variables from the specified TOML file.
        If the file does not exist or is empty, an empty frozendict is returned.
    """
    # File-Env by Mode
    file_path = base_dir / "config" / ".env" / f"{mode}.toml"

    # Load the TOML file and return the 'env' section as a frozendict
    env_data = get_toml_file(file_path).get("env", {})

    return frozendict(env_data)
