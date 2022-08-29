import os
import pathlib
import sys
from collections import UserDict

from .core import get_plugins
from .get_spoc import get_spoc_plugins
from .singleton import Singleton
from .tools import get_fields


class SimpleDict(UserDict):
    def __setitem__(self, key, value):
        if key in self.keys():
            raise KeyError(f"{{ {key} }} already exist!")
        super().__setitem__(key, value)


# Test
class API(Singleton):
    """
    API's Dicts
    """

    def init(self):
        keys = [
            # Schemas
            "types",
            "forms",
            "methods",
            "commands",
            # Databases
            "databases",
            "models",
        ]
        for key in keys:
            setattr(self, key, SimpleDict())


class Settings(Singleton):
    """
    settings = Settings()
    """

    def init(self, base_dir: pathlib.Path = None, is_cli: bool = False):
        """__init__ Only Runs Once Per Settings Project."""

        if not base_dir:
            raise Exception("Missing: Settings(base_dir=BASE_DIR)")

        # Self { Definitions }
        self.api = API()
        self.is_cli = is_cli
        self.base_dir = base_dir
        self.config = SimpleDict()
        self.plugins = None
        self.settings = None
        self.schema = None

        # Inject { Apps }
        base_apps = pathlib.Path(base_dir / "apps")
        if base_apps.exists():
            sys.path.insert(0, os.path.join(base_dir, "apps"))

    def load_apps(self, plugins: list[str] = None, installed_apps: list[str] = None):
        """Load Project { Apps }"""

        # Discovering { Plugin(s) }
        loaded_plugins = get_plugins(plugins, installed_apps)
        app_schema = get_spoc_plugins(loaded_plugins.plugins)

        # Self { Definitions }
        self.schema = app_schema
        self.plugins = loaded_plugins
        self.keys = [x for x in get_fields(self) if x not in ["init", "load_apps"]]
