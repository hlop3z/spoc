"""
    Framework
"""

import functools
import os
import pathlib
import sys

from .errors import MissingValue, error_message
from .get_spoc import get_spoc_plugins
from .imports import get_plugins
from .toml_app import TOML
from .tools import get_fields


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


def load_apps(self, installed_apps: list[str] = None):
    """Load { Apps }"""

    # Discovering { Plugin(s) }
    loaded_plugins = get_plugins(self.__plugins__, installed_apps)
    app_schema = get_spoc_plugins(loaded_plugins.plugins)

    # Self { Definitions }
    self.schema = app_schema.schema
    self.modules = app_schema.globals
    self.plugins = loaded_plugins


def init(
    self,
    base_dir: pathlib.Path = None,
    mode: str = None,
    plugins: list[str] = None,
    installed_apps: list[str] = None,
):
    """__init__ Only Runs Once Per Settings Project."""

    if not base_dir:
        raise MissingValue(error_message("Project(base_dir = pathlib.Path)"))

    # Self { Definitions }
    self.mode = mode
    self.base_dir = base_dir
    self.plugins = None
    self.schema = None
    self.__plugins__ = plugins

    # Inject { Apps }
    base_apps = pathlib.Path(base_dir / "apps")
    base_apps.mkdir(parents=True, exist_ok=True)
    if base_apps.exists():
        sys.path.insert(0, os.path.join(base_dir, "apps"))

    # Load { Config }
    spoc_toml = pathlib.Path(base_dir / "spoc.toml")
    if not spoc_toml.exists():
        TOML.init()

    # Load { Apps }
    if installed_apps:
        load_apps(self, installed_apps)

    # Collect { Keys }
    self.keys = [x for x in get_fields(self) if x not in ["init", "load_apps"]]


def create_singleton(name: str, plugins: list[str]):
    """Base { Singleton }"""

    custom_class = type(
        name,
        (FrameworkSingleton,),
        {
            "init": functools.partial(init, plugins=plugins),
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
