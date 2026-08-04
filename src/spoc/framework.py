"""
Core framework module for SPOC.

The Framework is the single declaration point and the composition root: the
kind set, inter-kind dependencies, and lifecycle hooks are stated once, on
one object. Construction is inert — all discovery happens in an explicit
``start(base_dir)`` step. Two Framework instances in one process are fully
independent.

Usage:
    from pathlib import Path
    import spoc

    framework = spoc.Framework("models", "views", dependencies={"views": ["models"]})

    model = framework.kind("models")   # @model  /  @model(name="user_account")
    view = framework.kind("views")

    @framework.on_ready
    def finalize(registry):
        ...  # every component of every kind is registered here

    framework.start(Path("/path/to/project"))

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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Local imports
from .components import Components
from .core.config_loader import DEFAULT_MODE, load_environment, load_spoc_toml
from .core.exceptions import SpocError, UnknownKindError
from .core.importer import FrameworkMode, Importer
from .core.registry import Component, Registry
from .inject_apps import inject_apps


@dataclass(frozen=True)
class Config:
    """
    Configuration container for the framework.

    Attributes:
        `project`: Project configuration (the ``[spoc]`` table)
        `environment`: Environment variables for the active mode
    """

    project: dict[str, Any]
    environment: Any


def build_config(base_dir: Path, echo: bool = False) -> Config:
    """
    Build a configuration object from ``spoc.toml`` in the given directory.

    ``spoc.toml`` is the only configuration file the kernel reads — anything
    else under the project's config directory belongs to the user.

    Args:
        base_dir: Base directory containing the configuration file
        echo: Whether to log warnings about missing configuration files

    Returns:
        Config object populated with project and environment data
    """
    raw = load_spoc_toml(base_dir).get("spoc", {})
    mode = raw.get("mode", DEFAULT_MODE)
    return Config(
        project=raw,
        environment=load_environment(base_dir, mode, echo=echo),
    )


class Framework:
    """
    The framework object — declaration point and composition root.

    Declares the closed kind set and inter-kind dependency order, hands out
    per-kind registration decorators, and owns the flat component registry
    that external surfaces project from. Construction has no side effects;
    ``start(base_dir)`` boots the project.
    """

    def __init__(
        self,
        *kinds: str,
        dependencies: dict[str, list[str]] | None = None,
        mode: FrameworkMode = "strict",
        echo: bool = False,
    ) -> None:
        """
        Declare a framework. Pure — no filesystem, path, or import effects.

        Args:
            *kinds: The closed kind set. Each kind is a module name
                (``<app>/<kind>.py``) and an identifier segment; validated,
                never normalized.
            dependencies: Inter-kind load order, e.g. ``{"views": ["models"]}``.
                Keys and values must be declared kinds.
            mode: "strict" raises on missing apps/modules; "loose" skips them.
            echo: Whether to log warnings about missing configuration files.
        """
        self._components = Components(*kinds)
        self.dependencies = dict(dependencies or {})
        for kind_name, deps in self.dependencies.items():
            self._require_kind(kind_name)
            for dep in deps:
                self._require_kind(dep)
        self.mode: FrameworkMode = mode
        self.echo = echo
        self.importer = Importer(mode=mode, kinds=self.kinds)
        self._ready_callbacks: list[Callable[[Registry], Any]] = []
        self._lifecycle_hooks: dict[str, dict[str, Callable[..., Any]]] = {}
        self._started = False
        self.base_dir: Path | None = None
        self.config: Config | None = None
        self.plugins: dict[str, OrderedDict[str, Any]] = {}
        self.installed_apps: list[str] = []

    # ── Declaration surface ───────────────────────────────────────────────

    @property
    def kinds(self) -> tuple[str, ...]:
        """The declared kind set (closed; fixed at construction)."""
        return self._components.kinds

    def _require_kind(self, kind: str) -> None:
        if kind not in self.kinds:
            raise UnknownKindError(kind, self.kinds)

    def kind(self, kind: str) -> Callable[..., Any]:
        """
        The registration decorator for a declared kind.

        The returned callable supports both forms:

            model = framework.kind("models")

            @model                        # name taken from the object
            class post: ...

            @model(name="user_account")   # explicit conforming name
            class UserAccount: ...

        Raises:
            UnknownKindError: If ``kind`` is not in the declared set.
        """
        self._require_kind(kind)

        def register(
            obj: Any = None,
            *,
            name: str | None = None,
            config: dict[str, Any] | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> Any:
            return self._components.register(
                kind, obj, name=name, config=config, metadata=metadata
            )

        register.__doc__ = f"Register an object as a {kind!r} component."
        return register

    def on_ready(
        self, callback: Callable[[Registry], Any]
    ) -> Callable[[Registry], Any]:
        """
        Register a finalize callback.

        Callbacks fire exactly once per start, in registration order, after
        every component is registered and before module initialization. They
        receive the completed registry — the place for cross-component builds
        (ORM tables, route trees, DI graphs). A callback error fails start.
        """
        self._ready_callbacks.append(callback)
        return callback

    def on_startup(
        self, kind: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Register a startup hook for every module of a kind.

        The hook is called with the set of the module's registered component
        objects, before the module's own ``initialize()``.

        Raises:
            UnknownKindError: If ``kind`` is not in the declared set.
        """
        self._require_kind(kind)

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._lifecycle_hooks.setdefault(kind, {})["startup"] = fn
            return fn

        return decorator

    def on_shutdown(
        self, kind: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Register a shutdown hook for every module of a kind.

        The hook is called with the set of the module's registered component
        objects, before the module's own ``teardown()``.

        Raises:
            UnknownKindError: If ``kind`` is not in the declared set.
        """
        self._require_kind(kind)

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._lifecycle_hooks.setdefault(kind, {})["shutdown"] = fn
            return fn

        return decorator

    # ── Reads ─────────────────────────────────────────────────────────────

    @property
    def started(self) -> bool:
        """True once ``start`` has completed successfully."""
        return self._started

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

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self, base_dir: Path | str) -> Framework:
        """
        Boot the project rooted at ``base_dir``.

        In order: inject the apps directory, load ``spoc.toml``, collect the
        mode-cascaded app list, load plugins, register app modules, discover
        declared components into the registry (loudly — a component that
        cannot be registered fails startup), fire ``on_ready`` callbacks,
        then initialize modules in dependency order.

        Raises:
            SpocError: If the framework is already started, or discovery,
                a ready callback, or initialization fails.
            CircularDependencyError: If module dependencies form a cycle.
        """
        if self._started:
            raise SpocError("Framework is already started")

        base_dir = Path(base_dir)
        inject_apps(base_dir)
        self.base_dir = base_dir
        self.config = build_config(base_dir, self.echo)
        self.plugins = self._collect_plugins()
        self._register_all_apps()
        self._register_hooks()

        self.importer.discover()
        for callback in self._ready_callbacks:
            callback(self.registry)
        self.importer.initialize()

        self._started = True
        return self

    def shutdown(self) -> Framework:
        """
        Tear down the application.

        Shuts down all modules in the reverse order of initialization,
        calling shutdown hooks as needed. A no-op if the framework never
        started.
        """
        if not self._started:
            return self
        self.importer.shutdown()
        self._started = False
        return self

    # ── Boot steps (private) ──────────────────────────────────────────────

    def _collect_plugins(self) -> dict[str, OrderedDict[str, Any]]:
        """
        Load all plugins declared in ``[spoc.plugins]``.

        Raises:
            AppNotFoundError: If a plugin reference names a missing module.
            AttributeError: If a plugin reference names a missing attribute.
        """
        assert self.config is not None
        plugins = self.config.project.get("plugins", {}) or {}
        plug_dict: dict[str, OrderedDict[str, Any]] = {}
        for group, modules in plugins.items():
            plug_dict[group] = OrderedDict()
            for mod_uri in modules:
                if mod_uri not in plug_dict[group]:
                    plug_dict[group][mod_uri] = self.importer.load_from_uri(mod_uri)
        return plug_dict

    def _register_modules(self, app: str) -> None:
        for mod in self.kinds:
            fq = f"{app}.{mod}"
            reqs = [f"{app}.{d}" for d in self.dependencies.get(mod, ())]
            self.importer.register(fq, dependencies=reqs)

    def _register_hooks(self) -> None:
        for kind_name, spec in self._lifecycle_hooks.items():
            self.importer.register_hook(
                pattern=f"*.{kind_name}",
                on_startup=spec.get("startup"),
                on_shutdown=spec.get("shutdown"),
            )

    @staticmethod
    def _collect_apps(app_mode: str, the_apps: dict) -> list:
        """Cascaded app list for a mode, order preserved, first wins."""
        installed_apps = []
        seen = set()

        # Define the order of modes to include
        mode_order = {
            "production": ["production"],
            "staging": ["staging", "production"],
            "development": ["development", "staging", "production"],
        }

        for mode in mode_order.get(app_mode, []):
            for app in the_apps.get(mode, []):
                if app not in seen:
                    seen.add(app)
                    installed_apps.append(app)

        return installed_apps

    def _register_all_apps(self) -> None:
        assert self.config is not None
        app_names = self._collect_apps(
            self.config.project.get("mode", DEFAULT_MODE),
            self.config.project.get("apps", {}),
        )
        for name in app_names:
            self._register_modules(name)
        self.installed_apps = app_names
