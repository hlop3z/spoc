"""
    Framework
"""

import functools
import os
import pathlib
import sys

from .errors import MissingValue, error_message
from .frozendict import FrozenDict
from .get_spoc import get_spoc_plugins
from .imports import get_plugins
from .toml_app import TOML
from .tools import get_fields
from .types import Project


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
    cls.core = Project(
        toml=self.toml,
        installed_apps=admin.installed_apps,
        schema=admin.schema,
        modules=admin.plugins.modules,
        plugins=admin.modules,
        settings=admin.settings,
        keys=["modules", "schema", "plugins", "settings", "installed_apps", "toml"],
    )
    return cls


def collect_installed_apps(self):
    """Collect All Apps"""
    # Step[1]: INIT { Values }
    admin = self
    app_mode = admin.app_mode
    settings = admin.settings
    apps = admin.apps
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

    self.load_apps(self, installed_apps=installed_apps)
    return installed_apps


def init(
    self,
    base_dir: pathlib.Path = None,
    mode: str = None,
    plugins: list[str] = None,
    app: object = None,
):
    """__init__ Only Runs Once Per Settings Project."""

    if not base_dir:
        raise MissingValue(error_message("Project(base_dir = pathlib.Path)"))

    # Step[1]: INIT { Definitions }
    all_fields = [
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
    disabled_fields = ["mode", "base_dir", "plugins"]
    for field in all_fields:
        if field not in disabled_fields:
            setattr(self, field, None)

    # Step[2]: Self { Definitions }
    self.mode = mode
    self.base_dir = base_dir
    self.__plugins__ = plugins

    # Step[3]: Inject { Apps }
    base_apps = pathlib.Path(base_dir / "apps")
    base_apps.mkdir(parents=True, exist_ok=True)
    if base_apps.exists():
        sys.path.insert(0, os.path.join(base_dir, "apps"))

    # Step[4]: TOML { Config }
    toml_file = pathlib.Path(base_dir / "spoc.toml")
    if not toml_file.exists():
        TOML.init()
    else:
        TOML.file = toml_file

    # Step[5]: TOML-Collect { Apps }
    toml_data = TOML.read()
    self.toml = FrozenDict(**toml_data.get("spoc", {}))
    self.apps = self.toml.get("apps", {})
    self.app_mode = self.toml.get("config", {}).get("mode", "development")

    # Step[6]: Load { Project }
    try:
        import project

        self.project = project
    except ImportError as exception:
        raise ValueError("Missing { project } module.") from exception

    # Step[7]: Load { Settings }
    if not hasattr(self.project, "settings"):
        raise ValueError("Missing { project.settings } module.")
    self.settings = self.project.settings

    # Step[8]: Collect { Apps }
    self.installed_apps = collect_installed_apps(self)

    # Finally: Collect { Keys }
    self.keys = [x for x in get_fields(self) if x not in ["init", "load_apps"]]

    create_project(self, app, base_dir)


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

    return create_singleton(name=name, plugins=plugins)
