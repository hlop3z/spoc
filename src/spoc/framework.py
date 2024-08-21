# -*- coding: utf-8 -*-
"""
Framework:
    - Apps (`packages`) folders
    - Components (`modules`) files
    - Extras (`objects`)
    - Settings
    - TOML files
"""

import os
import pathlib
from typing import Any, Dict, List, Optional

from .importer import create_framework, frozendict
from .inject import (
    collect_extras,
    collect_installed_apps,
    get_app_mode,
    get_toml_files,
    inject_apps_folder,
    load_envs,
)
from .singleton import Singleton

# Attempt to import the configuration module.
CONFIG = None
try:
    import config  # type: ignore

    CONFIG = config
except ImportError:
    CONFIG = None

if CONFIG:
    try:
        from config import settings  # type: ignore
    except ImportError as exception:
        raise ValueError("Missing { ./config/__init__.py } module.") from exception

    if not settings:
        raise ValueError("Missing { ./config/settings.py } module.")

    if not hasattr(settings, "BASE_DIR"):
        raise ValueError("Missing { BASE_DIR } in file { ./config/settings.py }.")

    # Core configuration and settings
    SETTINGS = settings
    BASE_DIR = settings.BASE_DIR

    # Inject the applications folder to the global namespace
    inject_apps_folder(BASE_DIR)

    # Load and parse configuration files
    TOML_DIR = get_toml_files(BASE_DIR)
    TOML_DIR = frozendict(TOML_DIR)
    MODE = get_app_mode(TOML_DIR)

    # Spoc TOML
    SPOC_TOML = frozendict(TOML_DIR.get("spoc", {}).get("spoc", {}))
    EXTRAS = SPOC_TOML.get("extras", {})

    # Load environment variables
    TOML_ENV = load_envs(BASE_DIR, MODE)

    # Force `DEBUG` on Settings
    if not hasattr(settings, "DEBUG"):
        setattr(settings, "DEBUG", SPOC_TOML.get("debug", False))

    # Set (`CONFIG`, `ENV`, `MODE`, `SPOC`) on Settings
    setattr(settings, "CONFIG", TOML_DIR)
    setattr(settings, "ENV", TOML_ENV)
    setattr(settings, "MODE", MODE)
    setattr(settings, "SPOC", SPOC_TOML)

    class Spoc(Singleton):
        """
        A Singleton representing the entire `Framework`.
        """

        # Core
        base_dir: pathlib.Path = BASE_DIR
        mode: str = MODE
        config: Dict[str, Dict] = TOML_DIR
        settings: Any = SETTINGS
        spoc_toml: Any = SPOC_TOML
        environment: Any = TOML_ENV

        # Python Modules
        module: Any = None

        # Apps & Components
        installed_apps: List | None = None
        extras: Dict[Any, Any] | None = None
        components: Dict[Any, Any] | None = None

        def init(self, plugins: Optional[List] = None) -> None:
            """
            Initialize the framework by collecting installed applications and extras.

            Args:
                plugins (list | None): A list of plugins to initialize with the framework.
            """
            # GLOBALS Modules
            installed_apps = collect_installed_apps(TOML_DIR, SETTINGS)
            extras = collect_extras(EXTRAS, SETTINGS)

            # Plugins
            plugins = plugins or []
            framework = create_framework(
                plugins=plugins, installed_apps=installed_apps, extras=extras
            )

            # Output Model
            self.installed_apps = installed_apps
            self.extras = framework.extras
            self.module = framework.module
            self.components = framework.plugin

            # Change Dir
            os.chdir(BASE_DIR)

        @staticmethod
        def keys() -> List[str]:
            """
            Get the keys for the framework object.
            """
            return [
                # Core
                "base_dir",
                "module",
                "installed_apps",
                # Settings
                "config",
                "mode",
                "settings",
                "spoc_toml",
                # Components
                "components",
                "extras",
            ]


def init(plugins: Optional[List] = None):
    """
    Initialize the framework by collecting installed `apps` and `extras`.

    Args:
        plugins (list | None): A list of plugins (`files`) to initialize within the framework.

    Examples:
    ::

        spoc.init(["models", "views"]) # will collect from `models.py` and `views.py`
    """
    return Spoc(plugins=plugins)
