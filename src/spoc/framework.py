"""
Core framework module for SPOC.

The Framework is the composition root: it owns its importer (and therefore
its registry and hooks), loads configuration, discovers apps, and manages
lifecycle. Two Framework instances in one process are fully independent.

Usage:
    from spoc.framework import Framework, Schema
    from pathlib import Path

    schema = Schema(
        modules=["models", "views"],
        dependencies={"views": ["models"]},
        hooks={}
    )
    framework = Framework(base_dir=Path("/path/to/app"), schema=schema)

    record = framework.resolve("models:blog.post")   # a Component record
    for component in framework.registry.by_kind("models"):
        ...  # project routes, schemas, docs from records

    framework.shutdown()

The kernel describes — it never executes. Resolution is a pure lookup;
invocation belongs to the surfaces built on top.
"""

from __future__ import annotations

# Standard library imports
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, NotRequired, TypedDict

# Local imports
from .core.config_loader import load_configuration, load_environment, load_spoc_toml
from .core.importer import FrameworkMode, Importer
from .core.registry import Component, Registry
from .inject_apps import inject_apps

DEFAULT_MODE = "development"


class Hook(TypedDict):
    """
    Type definition for lifecycle hooks.

    A dictionary containing optional startup and shutdown callables
    that are executed during framework initialization and termination.
    Each callable receives the set of component objects registered for
    the module it fires on.
    """

    startup: NotRequired[Callable[[set[Any]], Any]]
    shutdown: NotRequired[Callable[[set[Any]], Any]]


@dataclass
class Schema:
    """
    Schema definition for application modules and their dependencies.

    ``modules`` is also the project's closed kind set: objects declared in
    ``<app>/<module>.py`` are components of kind ``<module>``, and no other
    kinds exist (layout is taxonomy).
    """

    modules: list[str]
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    hooks: dict[str, Hook] = field(default_factory=dict)


@dataclass(frozen=True)
class Config:
    """
    Configuration container for the framework.

    Attributes:
        `project`: Project configuration (the ``[spoc]`` table)
        `settings`: Settings module
        `environment`: Environment variables for the active mode
    """

    project: dict[str, Any]
    settings: Any
    environment: Any


def build_config(base_dir: Path, echo: bool = False) -> Config:
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
        environment=load_environment(base_dir, mode, echo=echo),
    )


class Framework:
    """
    Core framework class for SPOC applications — the composition root.

    Manages the lifecycle of an application including module loading,
    dependency resolution, and plugin registration, and owns the flat
    component registry that external surfaces project from.
    """

    def _collect_plugins(self) -> dict[str, OrderedDict[str, Any]]:
        """
        Collect and load all configured plugins.

        Loads plugins from URIs defined in the configuration and organizes
        them into a hierarchical dictionary by group.

        Returns:
            Dictionary of plugin groups with their loaded module instances
        """
        plugins = self.config.project.get("plugins", {})
        plug_dict: dict[str, OrderedDict[str, Any]] = {}
        for group, mods in getattr(self.config.settings, "PLUGINS", {}).items():
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
            schema: Schema describing modules (the kind set) and dependencies.
            echo: Whether to echo debug information during operations.
            mode: Whether to enforce modules (files.py) in all apps at startup.
        """
        inject_apps(base_dir)

        self.echo = echo
        self.base_dir = base_dir
        self.schema = schema
        self.installed_apps: list[str] = []
        self.importer = Importer(mode=mode, kinds=tuple(schema.modules))
        self.config = build_config(base_dir, echo)
        self.plugins = self._collect_plugins()

        # Start the framework
        self.startup()

    @property
    def registry(self) -> Registry:
        """The flat component registry — the single read surface."""
        return self.importer.registry

    def resolve(self, identifier: str) -> Component:
        """
        Resolve a canonical identifier (``kind:namespace.object_name``) to
        its registry record.

        A pure lookup: the resolved object is returned unexecuted. Failures
        raise per segment — kind, then namespace, then object_name — each
        error naming the failing segment, its value, and the valid
        candidates at that step.

        Raises:
            MalformedIdentifierError: If the string doesn't parse.
            InvalidSegmentError: If a segment violates the grammar.
            UnknownKindError: If the kind is not declared.
            UnknownNamespaceError: If no such namespace holds that kind.
            UnknownObjectError: If the name is absent in kind:namespace.
        """
        return self.registry.resolve(identifier)

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
            self._register_modules(name)
        # Store for later use
        self.installed_apps = app_names
        return self

    def startup(self) -> Framework:
        """
        Bootstrap the application.

        Registers all configured applications and hooks, discovers declared
        components into the registry (loudly — a component that cannot be
        registered fails startup), and initializes modules in dependency
        order.

        Returns:
            Self instance for method chaining
        """
        self._register_all_apps()
        self._register_hooks()
        self.importer.startup()
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
