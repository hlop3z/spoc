"""
Core framework module for SPOC.

This module provides the foundational Framework class that manages application lifecycle,
module loading, plugin registration, and dependency handling within SPOC applications.

Usage:
    from spoc.framework import Framework, Schema
    from pathlib import Path

    schema = Schema(
        modules=["models", "views"],
        dependencies={"views": ["models"]},
        hooks={}
    )
    framework = Framework(base_dir=Path("/path/to/app"), schema=schema)
    framework.startup()
    # ... run your app ...
    framework.shutdown()

The framework is designed for modular, testable, and extensible applications.
It supports dynamic module loading, dependency management, and plugin systems.
"""

from __future__ import annotations

# Standard library imports
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List, NotRequired, TypedDict

# Local imports
from .core.config_loader import load_configuration, load_environment, load_spoc_toml
from .core.importer import FrameworkMode, Importer
from .inject_apps import inject_apps

DEFAULT_MODE = "development"


class Hook(TypedDict):
    """
    Type definition for lifecycle hooks.

    A dictionary containing optional startup and shutdown callables
    that are executed during framework initialization and termination.
    """

    startup: NotRequired[Callable[[ModuleType], Any]]
    shutdown: NotRequired[Callable[[ModuleType], Any]]


@dataclass
class Schema:
    """
    Schema definition for application modules and their dependencies.

    Defines a structure for modules to be loaded, their dependencies,
    and associated lifecycle hooks.
    """

    modules: List[str]
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    hooks: Dict[str, Hook] = field(default_factory=dict)


@dataclass(frozen=True)
class Config:
    """
    Configuration container for the framework.

    Holds project configuration, settings, and environment variables
    loaded from configuration files.

    Attributes:
        `project`: Project configuration
        `settings`: Settings configuration
        `environment`: Environment variables
    """

    project: Dict[str, Any]
    settings: Any
    environment: Any


def build_config(base_dir: Path) -> Config:
    """
    Build a configuration object from files in the specified directory.

    Args:
        base_dir: Base directory containing configuration files

    Returns:
        Config object populated with project, settings and environment data
    """
    raw = load_spoc_toml(base_dir).get("spoc", {})
    mode = raw.get("mode", DEFAULT_MODE)
    return Config(
        project=raw,
        settings=load_configuration(base_dir),
        environment=load_environment(base_dir, mode),
    )


class Framework:
    """
    Core framework class for SPOC applications.

    Manages the lifecycle of an application including module loading,
    dependency resolution, and plugin registration. Provides a structured
    way to bootstrap and tear down applications.
    """

    installed_apps: list[str] = []
    components: SimpleNamespace = SimpleNamespace()

    def _collect_plugins(self) -> Dict[str, OrderedDict[str, Any]]:
        """
        Collect and load all configured plugins.

        Loads plugins from URIs defined in the configuration and organizes
        them into a hierarchical dictionary by group.

        Returns:
            Dictionary of plugin groups with their loaded module instances
        """
        plugins = self.config.project.get("plugins", {})
        plug_dict: Dict[str, OrderedDict[str, Any]] = {}
        for group, mods in self.config.settings.PLUGINS.items():
            if group not in plugins:
                plugins[group] = []
            plugins[group].extend(mods)
        if plugins:
            for group, modules in plugins.items():
                if group not in plug_dict:
                    plug_dict[group] = OrderedDict()
                for mod_uri in modules:
                    if mod_uri not in plug_dict[group]:
                        plug_dict[group][mod_uri] = self.importer.load_from_uri(mod_uri)
        return plug_dict

    def __init__(
        self,
        base_dir: Path,
        schema: Schema,
        echo: bool = False,
        mode: FrameworkMode = "strict",
    ) -> None:
        """
        Initialize the framework instance.

        Args:
            base_dir: Base directory for the application.
            schema: Schema describing modules and dependencies.
            echo: Whether to echo debug information during operations.
            mode: Whether to enforce modules (files.py) in all apps at startup.
        """
        inject_apps(base_dir)

        self.echo = echo  # Store for potential future use
        self.base_dir = base_dir
        self.schema = schema
        self.importer = Importer(mode=mode)
        self.config = build_config(base_dir)
        self.plugins = self._collect_plugins()

        # Start the framework
        self.startup()

    def get_component(self, kind: str, name: str) -> Any:
        """Get a framework component by <kind>.<name>"""
        if hasattr(self.components, kind):
            return getattr(self.components, kind).get(name)
        return None

    def _register_modules(self, app: str) -> None:
        for mod in self.schema.modules:
            fq = f"{app}.{mod}"
            reqs = [f"{app}.{d}" for d in self.schema.dependencies.get(mod, ())]
            self.importer.register(fq, dependencies=reqs)

    def _register_hooks(self) -> None:
        for mod_name, spec in self.schema.hooks.items():
            if not spec:
                continue  # Skip if no hooks defined
            self.importer.register_hook(
                pattern=f"*.{mod_name}",
                on_startup=spec.get("startup"),
                on_shutdown=spec.get("shutdown"),
            )

    def _register_app(self, app_name: str) -> Framework:
        self._register_modules(app_name)
        self._register_hooks()
        return self

    @staticmethod
    def _collect_apps(app_mode: str, the_apps: dict, py_apps: list) -> list:
        """Collect apps based on the specified mode with preserved order and no duplicates."""
        installed_apps = []
        seen = set()

        # Define the order of modes to include
        mode_order = {
            "production": ["production"],
            "staging": ["staging", "production"],
            "development": ["development", "staging", "production"],
        }

        for app in py_apps:
            if app not in seen:
                seen.add(app)
                installed_apps.append(app)

        for mode in mode_order.get(app_mode, []):
            for app in the_apps.get(mode, []):
                if app not in seen:
                    seen.add(app)
                    installed_apps.append(app)

        return installed_apps

    def _register_all_apps(self) -> Framework:
        py_apps = getattr(self.config.settings, "INSTALLED_APPS", [])
        app_names = self._collect_apps(
            self.config.project.get("mode", DEFAULT_MODE),
            self.config.project.get("apps", {}),
            py_apps,
        )
        for name in app_names:
            self._register_app(name)
        # Store for later use
        self.installed_apps = app_names
        return self

    def _init_components(self) -> None:
        for mod in self.schema.modules:
            if mod not in self.importer.components:
                self.importer.components[mod] = {}
        self.components = SimpleNamespace(**self.importer.components)

    def startup(self) -> Framework:
        """
        Bootstrap the application.

        Registers all configured applications, initializes modules in dependency
        order, and loads all plugins.

        Returns:
            Self instance for method chaining
        """
        self._register_all_apps()
        self.importer.startup()
        self._init_components()
        return self

    def shutdown(self) -> Framework:
        """
        Tear down the application.

        Shuts down all modules in the reverse order of initialization,
        calling shutdown hooks as needed.

        Returns:
            Self instance for method chaining
        """
        self.importer.shutdown()
        return self
