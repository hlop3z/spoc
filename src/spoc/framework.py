"""
    FrameWork
"""

import os

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


from . import installer

config = None
try:
    import config
except ImportError as exception:
    try:
        installer.create_base()
    except:
        config = None

if config:
    try:
        from config import settings
    except ImportError as exception:
        raise ValueError("Missing { ./config/__init__.py } module.") from exception

    if not settings:
        raise ValueError("Missing { ./config/settings.py } module.")

    if not hasattr(settings, "BASE_DIR"):
        raise ValueError(
            """Missing { `BASE_DIR = pathlib.Path(__file__).parents[1]` } in file { ./config/settings.py }."""
        )


    # Core
    PROJECT = config
    SETTINGS = settings
    BASE_DIR = settings.BASE_DIR

    # Global Methods
    inject_apps_folder(BASE_DIR)

    # Global Variables
    TOML_DIR = get_toml_files(BASE_DIR)
    MODE = get_app_mode(TOML_DIR)
    EXTRAS = TOML_DIR["spoc"].get("spoc", {}).get("extras", {})

    # Global Fixed
    TOML_DIR["env"] = load_envs(BASE_DIR, MODE)
    TOML_DIR = frozendict(TOML_DIR)


    @singleton
    class Spoc:
        """Core Object(Singleton) for the whole Framework"""

        base_dir = BASE_DIR
        config = TOML_DIR
        mode = MODE
        project = PROJECT
        settings = SETTINGS

        def init(self, plugins: list = None):
            """Finally: Collect { Keys }"""
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
        def keys():
            """Object Keys"""
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
