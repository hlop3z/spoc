"""
    Framework
"""

import functools
import os
import pathlib
import sys

from .frozendict import FrozenDict
from .get_spoc import get_spoc_plugins
from .imports import get_plugins
from .project_core import BASE_DIR, PROJECT, SETTINGS
from .toml_app import TOML
from .tools import get_fields
from .types import Project

CORE_KEYS = [
    "app_mode",
    "apps",
    "base_dir",
    "installed_apps",
    "mode",
    "modules",
    "plugins",
    "project",
    "schema",
    "settings",
    "toml",
]
PROJECT_KEYS = [
    "modules",
    "schema",
    "components",
    "settings",
    "installed_apps",
    "toml",
    "pyproject",
    "keys",
]


class FrameworkSingleton:
    """Class: Create a Singleton"""

    def __new__(cls, *args, **kwargs):
        it_id = "__it__"
        it = cls.__dict__.get(it_id, None)
        if it is not None:
            return it
        it = object.__new__(cls)
        setattr(cls, it_id, it)
        it.init(cls, *args, **kwargs)
        return it

    def init(self, *args, **kwargs):
        """Class __init__ Replacement"""


def create_project(self, cls, base_dir):
    """Wraps The Project Configurations"""
    # Step[1]: INIT { Admin }
    admin = self

    # Step[2]: Self { Definitions }
    cls.admin = admin
    cls.base_dir = base_dir
    cls.mode = admin.app_mode
    cls.project = admin.project
    core_plugins = admin.plugins

    # Cleaned Modules (IF: Founded)
    core_modules = None
    if core_plugins:
        core_modules = core_plugins.modules

    cls.core = Project(
        toml=self.toml,
        installed_apps=admin.installed_apps,
        schema=admin.schema,
        modules=core_modules,
        components=admin.modules,
        settings=admin.settings,
        keys=[x for x in PROJECT_KEYS if x not in ["keys"]],
        pyproject=admin.pyproject,
    )
    return cls


def collect_installed_apps(toml_dir, settings=SETTINGS):
    """Collect All Apps"""

    # Step[1]: INIT { Values }
    app_mode = toml_dir["spoc"].get("mode", "development")
    apps = toml_dir["spoc"].get("apps", {})
    installed_apps = []

    # Step[2]: Collect Apps
    match app_mode:
        case "custom":
            if hasattr(settings, "INSTALLED_APPS"):
                installed_apps.extend(settings.INSTALLED_APPS)
        case "production":
            installed_apps.extend(apps.get("production", []))
        case "staging":  # production + staging
            installed_apps.extend(apps.get("production", []))
            installed_apps.extend(apps.get("staging", []))
        case "development":  # production + development
            installed_apps.extend(apps.get("production", []))
            installed_apps.extend(apps.get("development", []))

    return installed_apps


def inject_apps_folder():
    """Inject { ./apps }"""
    base_apps = pathlib.Path(BASE_DIR / "apps")
    base_apps.mkdir(parents=True, exist_ok=True)
    if base_apps.exists():
        sys.path.insert(0, os.path.join(BASE_DIR, "apps"))


def get_toml_files():
    """Collect All { TOML } Files"""

    # Get Base Directory
    base_dir = BASE_DIR

    # Step[1]: TOML { Config }
    toml_file = pathlib.Path(base_dir / "spoc.toml")
    pytoml_file = pathlib.Path(base_dir / "pyproject.toml")

    # Step[2]: Load { TOML }
    TOML.file = toml_file
    if not toml_file.exists():
        TOML.init()
    if pytoml_file.exists():
        pyproject_toml = FrozenDict(**TOML.read(pytoml_file))
    else:
        pyproject_toml = {}

    spoc_toml = TOML.read()

    return {
        "spoc": FrozenDict(**spoc_toml.get("spoc", {})),
        "pyproject": pyproject_toml,
    }


def get_app_mode(toml_dir):
    """Get App { Mode }"""

    mode = toml_dir["spoc"].get("mode", "development")
    # Fix: Mode IF (Custom)
    if mode == "custom":
        mode = toml_dir["spoc"].get("custom_mode", "development")
    return mode


# GLOBALS
TOML_DIR = get_toml_files()
MODE = get_app_mode(TOML_DIR)
INSTALLED_APPS = collect_installed_apps(TOML_DIR)

# GLOBAL INJECTIONS
inject_apps_folder()


def init(
    self,
    plugins: list[str] = None,
    app: object = None,
):
    """__init__ Only Runs Once Per Settings Project."""

    # Step[1]: Set Core Settings
    base_dir = BASE_DIR

    # Step[2]: INIT { Definitions }
    disabled_fields = ["base_dir"]
    for field in CORE_KEYS:
        if field not in disabled_fields:
            setattr(self, field, None)

    # Step[3]: Self { Definitions }
    self.project = PROJECT
    self.settings = SETTINGS
    self.base_dir = base_dir
    self.__plugins__ = plugins
    self.__theclass__ = app

    # Step[5]: TOML-Collect { Apps }
    self.toml = TOML_DIR["spoc"]
    self.app_mode = MODE
    self.pyproject = TOML_DIR["pyproject"]

    # Step[6]: Install { Apps }
    self.load_apps(self, installed_apps=INSTALLED_APPS)
    self.installed_apps = INSTALLED_APPS

    # Step[7]: Create <class: Project>
    self.core = Project(**{k: None for k in PROJECT_KEYS})

    # Step[8]: Create <class: Project>
    create_project(self, self.__theclass__, self.base_dir)

    # Finally: Collect { Keys }
    self.keys = [x for x in get_fields(self) if x not in ["init", "load_apps"]]

    # Fix: App-Mode IF (Custom)
    if self.app_mode == "custom":
        self.app_mode = self.toml.get("custom_mode", "development")


def load_apps(self, installed_apps: list[str] = None):
    """Load { Apps }"""

    if installed_apps and isinstance(installed_apps, list | set):
        # Discovering { Plugin(s) }
        loaded_plugins = get_plugins(self.__plugins__, installed_apps)
        app_schema = get_spoc_plugins(loaded_plugins.plugins)

        # Self { Definitions }
        self.schema = app_schema.schema
        self.modules = app_schema.modules
        self.plugins = loaded_plugins


def create_singleton(name: str, plugins: list[str]):
    """Base { Singleton }"""

    custom_class = type(
        name,
        (FrameworkSingleton,),
        {
            "init": functools.partial(init, plugins=plugins),
            "load_apps": load_apps,
        },
    )

    return custom_class


def framework(cls):
    """Create { Singleton }"""

    module = cls.__module__
    if cls.__module__ == "__main__":
        module = "main"

    name = cls.__name__

    if not hasattr(cls, "plugins"):
        raise Exception(
            f"Class <{module}.{name}> Must Define What <Plugins> To Look For."
        )

    plugins = cls.plugins
    custom_class = create_singleton(name=name, plugins=plugins)
    return custom_class
