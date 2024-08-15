# -*- coding: utf-8 -*-
"""
FrameWork
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
from .singleton import singleton

# Attempt to import the configuration module, create base if it does not exist.
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
    MODE = get_app_mode(TOML_DIR)
    EXTRAS = TOML_DIR["spoc"].get("spoc", {}).get("extras", {})

    # Load environment variables
    TOML_DIR["env"] = load_envs(BASE_DIR, MODE)
    TOML_DIR = frozendict(TOML_DIR)

    @singleton
    class Spoc:
        """Core Object (Singleton) for the whole Framework."""

        # Core
        base_dir: pathlib.Path = BASE_DIR
        config: Dict[str, Dict] = TOML_DIR
        mode: str = MODE
        settings: Any = SETTINGS
        environment: Any = TOML_DIR.get("env", {})

        # Python Modules
        module: Any = None

        # App
        installed_apps: List | None = None
        extras: Dict[Any, Any] | None = None
        component: Dict[Any, Any] | None = None

        def init(self, plugins: Optional[List] = None) -> None:
            """
            Initialize the framework by collecting installed applications and extras.

            Args:
                plugins (Optional[List]): A list of plugins to initialize with the framework.
            """
            # GLOBALS
            installed_apps = collect_installed_apps(TOML_DIR, SETTINGS)
            extras = collect_extras(EXTRAS)

            plugins = plugins or []
            framework = create_framework(
                plugins=plugins, installed_apps=installed_apps, extras=extras
            )

            # Output Model
            self.installed_apps = installed_apps
            self.extras = framework.extras
            self.module = framework.module
            self.component = framework.plugin

            os.chdir(BASE_DIR)

        @staticmethod
        def keys() -> List[str]:
            """
            Get the list of keys for the framework object.

            Returns:
                List[str]: A list of attribute keys.
            """
            return [
                "base_dir",
                "config",
                "installed_apps",
                "mode",
                "project",
                "settings",
                "extras",
                "module",
                "component",
            ]
