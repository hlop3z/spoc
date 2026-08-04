"""
Dynamic module importing and lifecycle management system.

This module provides a class-based API for dynamically loading modules,
caching them for efficient reuse, and managing their initialization
and teardown in dependency order. Discovery of declared components happens
here at startup: every module's SPOC-marked objects are registered into the
importer's flat :class:`~spoc.core.registry.Registry`, loudly — a declared
component that cannot be registered fails startup with a precise error.

Usage:
    from spoc.core.importer import Importer
    importer = Importer(kinds=("models", "views"))
    importer.register("myapp.models", dependencies=["myapp.utils"])
    importer.startup()
    # ... use importer.registry ...
    importer.shutdown()

The Importer is a plain class: each instance owns its cache, its dependency
graph, its hooks, and its registry. Two importers in one process are fully
independent.
"""

from __future__ import annotations

# Standard library imports
import dataclasses
import graphlib
import importlib
import logging
import re
import sys
from collections.abc import Callable
from re import Pattern
from types import ModuleType
from typing import Any, Literal

# Local imports
from .components_discovery import discover_components
from .exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    ModuleNotCachedError,
    SpocError,
)
from .registry import Registry

logger = logging.getLogger("spoc")


type FrameworkMode = Literal["strict", "loose"]


@dataclasses.dataclass
class ModuleHooks:
    """Container for module lifecycle hooks."""

    generic: dict[str, Any] = dataclasses.field(default_factory=dict)
    pattern: dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class HookPattern:
    """Pattern matching for module hooks."""

    pattern: Pattern[str] | None = None
    method: Callable[[set[Any]], None] | None = None


class ModuleInfo:
    """
    Information about a dynamically loaded module.

    Stores metadata and lifecycle hooks for a module.

    Attributes:
        name: The module name
        module: The loaded module object
        dependencies: List of module names this module depends on
        initialize_func: Name of the initialization function in the module, or None
        teardown_func: Name of the teardown function in the module, or None
        initialized: Whether the module has been initialized
    """

    def __init__(
        self,
        name: str,
        module: ModuleType,
        dependencies: list[str] | None = None,
        initialize_func: str | None = "initialize",
        teardown_func: str | None = "teardown",
    ) -> None:
        self.name = name
        self.module = module
        self.dependencies = dependencies or []
        self.initialize_func = initialize_func
        self.teardown_func = teardown_func
        self.initialized = False

    def has_initialize(self) -> bool:
        """True if the module has an initialize function."""
        return self.initialize_func is not None and hasattr(
            self.module, self.initialize_func
        )

    def has_teardown(self) -> bool:
        """True if the module has a teardown function."""
        return self.teardown_func is not None and hasattr(
            self.module, self.teardown_func
        )

    def initialize(self) -> None:
        """
        Initialize the module if it has an initialize function.

        Sets the initialized flag to True after successful initialization.
        """
        if self.has_initialize() and not self.initialized:
            logger.debug("Calling initialize for module %s", self.name)
            initialize_func = getattr(self.module, self.initialize_func or "initialize")
            initialize_func()
            self.initialized = True
        else:
            logger.debug("Skipping initialization for module %s", self.name)

    def teardown(self) -> None:
        """
        Tear down the module if it has a teardown function.

        Resets the initialized flag to False after successful teardown.
        """
        if self.has_teardown() and self.initialized:
            logger.debug("Calling teardown for module %s", self.name)
            teardown_func = getattr(self.module, self.teardown_func or "teardown")
            teardown_func()
            self.initialized = False
        else:
            logger.debug("Skipping teardown for module %s", self.name)


class Importer:
    """
    Dynamic module importer with caching, lifecycle, and the registry.

    This class provides a clean API for:
    1. Dynamically importing modules at runtime
    2. Caching modules for efficient reuse
    3. Managing module lifecycle (initialization/teardown) based on dependencies
    4. Discovering declared components into the flat registry at startup

    Each instance is fully independent — cache, graph, hooks, and registry
    are all instance state. Instances are not thread-safe: build and start
    an importer from a single thread.

    Attributes:
        registry: The flat component registry this importer populates.
        module_hooks: Hooks to apply to modules during lifecycle events.
        on_startup_name: Name of the function called for module initialization.
        on_shutdown_name: Name of the function called for module teardown.
    """

    def __init__(
        self,
        on_startup_name: str | None = "initialize",
        on_shutdown_name: str | None = "teardown",
        mode: FrameworkMode = "strict",
        kinds: tuple[str, ...] = (),
    ) -> None:
        """
        Initialize a new Importer instance.

        Args:
            on_startup_name: Name of the initialization function in modules, or None
            on_shutdown_name: Name of the teardown function in modules, or None
            mode: "strict" raises on missing apps/modules; "loose" skips them.
            kinds: The declared (closed) kind set for the registry.
        """
        self.registry = Registry(kinds)
        self.module_hooks = ModuleHooks()
        self._module_cache: dict[str, ModuleInfo] = {}
        # node -> set of predecessors (its dependencies), fed to graphlib
        self._dependency_graph: dict[str, set[str]] = {}
        self.mode = mode
        self.on_startup_name = on_startup_name
        self.on_shutdown_name = on_shutdown_name

    def load(self, name: str) -> ModuleType | None:
        """
        Dynamically load a module by name.

        If the module is already in the cache, returns the cached module.
        Otherwise, imports the module and adds it to the cache.

        Raises:
            AppNotFoundError: If the module cannot be found (strict mode).
        """
        if self.has(name):
            return self._module_cache[name].module

        try:
            module = importlib.import_module(name)
            module_info = ModuleInfo(name=name, module=module)
            self._module_cache[name] = module_info
            self._dependency_graph.setdefault(name, set())
            return module
        except ImportError as e:
            if self.mode == "strict":
                raise AppNotFoundError(name) from e
            return None

    def register(
        self,
        name: str,
        dependencies: list[str] | None = None,
    ) -> ModuleType | None:
        """
        Register a module with dependencies and lifecycle hooks.

        Raises:
            AppNotFoundError: If the module cannot be found (strict mode).
        """
        # Load the module if not already loaded (strict mode raises in load())
        module = self.load(name)
        if module is None:
            return None

        # Update the module info with dependencies
        module_info = self._module_cache.get(name)
        assert module_info is not None, f"Module {name} not found in cache"
        module_info.dependencies = dependencies or []

        # Add dependencies to the graph
        for dep in module_info.dependencies:
            if not self.has(dep):
                self.load(dep)
                logger.debug("Loaded dependency: %s", dep)
            self._add_dependency(name, dep)

        return module

    def _add_dependency(self, name: str, dep: str) -> None:
        """Record that module `name` depends on module `dep`."""
        self._dependency_graph.setdefault(dep, set())
        self._dependency_graph.setdefault(name, set()).add(dep)

    def load_from_uri(self, uri: str) -> Any:
        """
        Load a function from a full URI like 'package.module.func'.

        Raises:
            AppNotFoundError: If the module cannot be imported (any mode —
                a URI names a specific attribute, so a missing module is
                always an error, even in loose mode).
            AttributeError: If the module lacks the named attribute.
        """
        parts = uri.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError("URI must be in the form 'package.module.function'")

        module_path, func_name = parts
        module = self.load(module_path)
        if module is None:
            raise AppNotFoundError(module_path)

        if not hasattr(module, func_name):
            raise AttributeError(
                f"Module '{module_path}' has no attribute '{func_name}'"
            )

        return getattr(module, func_name)

    def has(self, name: str) -> bool:
        """True if a module is in the cache."""
        return name in self._module_cache

    def get(self, name: str) -> ModuleType:
        """
        Get a module from the cache.

        Raises:
            ModuleNotCachedError: If the module is not in the cache.
        """
        if not self.has(name):
            raise ModuleNotCachedError(name)
        return self._module_cache[name].module

    def clear(self, name: str) -> None:
        """
        Remove a module from the cache (does not unload from sys.modules).
        """
        if self.has(name):
            module_info = self._module_cache.pop(name)
            if module_info.initialized and module_info.has_teardown():
                module_info.teardown()

    # ── Component discovery — loud, once, into the flat registry ──────────

    def _register_components(self, module_name: str) -> None:
        """
        Register every component declared in `module_name` into the registry.

        Raises:
            SpocError: If a declared component cannot be registered — a
                kind/location mismatch, an invalid segment, a duplicate
                identifier, or an underivable namespace. Never a silent drop.
        """
        discover_components(self.registry, self.get(module_name), module_name)

    def _module_components(self, module_name: str) -> set[Any]:
        """Registered objects belonging to `module_name` (for hooks)."""
        pkg, _, mod = module_name.rpartition(".")
        namespace = pkg.split(".")[0] if pkg else ""
        return {
            c.object for c in self.registry.by_kind(mod) if c.namespace == namespace
        }

    def _call_hook(
        self, hook_type: Literal["startup", "shutdown"], module_name: str
    ) -> None:
        """
        Call a lifecycle hook for a module with its registered objects.

        A generic (exact-name) hook overrides pattern hooks per hook type:
        pattern hooks still fire for a hook type the generic entry does not
        define.
        """
        instance = self._module_components(module_name)

        hook = self.module_hooks.generic.get(module_name)
        if hook:
            fn = hook.get(hook_type)
            if callable(fn):
                fn(instance)
                return

        for current in self.module_hooks.pattern.values():
            hp = current.get(hook_type)
            if (
                hp
                and hp.pattern
                and hp.pattern.fullmatch(module_name)
                and callable(hp.method)
            ):
                hp.method(instance)

    def _module_order(self) -> list[str]:
        """
        Cached modules in dependency order (dependencies first).

        Raises:
            CircularDependencyError: If the dependency graph has a cycle.
        """
        try:
            order = graphlib.TopologicalSorter(self._dependency_graph).static_order()
            return [m for m in order if m in self._module_cache]
        except graphlib.CycleError as e:
            raise CircularDependencyError([str(n) for n in e.args[1]]) from e

    def discover(self) -> None:
        """
        Register all declared components into the registry.

        Discovery runs across every module before any initialization, so
        duplicate identifiers and kind mismatches fail startup before any
        module's initialization side effects run.

        Raises:
            CircularDependencyError: If there are circular dependencies.
            SpocError: If discovery of any module fails.
        """
        try:
            self.on_startup()
            for module_name in self._module_order():
                self._register_components(module_name)
        except (CircularDependencyError, SpocError):
            raise
        except Exception as e:
            raise SpocError(f"Error during discovery: {e}") from e

    def initialize(self) -> None:
        """
        Initialize modules in dependency order, firing startup hooks.

        Raises:
            CircularDependencyError: If there are circular dependencies.
            SpocError: If initialization of any module fails.
        """
        try:
            module_order = self._module_order()
            logger.debug("Module initialization order: %s", module_order)
            for module_name in module_order:
                logger.debug("Initializing module: %s", module_name)
                self._call_hook("startup", module_name)
                self._module_cache[module_name].initialize()
        except (CircularDependencyError, SpocError):
            raise
        except Exception as e:
            raise SpocError(f"Error during startup: {e}") from e

    def startup(self) -> None:
        """
        Discover declared components, then initialize modules in dependency
        order. Equivalent to ``discover()`` followed by ``initialize()``.

        Raises:
            CircularDependencyError: If there are circular dependencies.
            SpocError: If discovery or initialization of any module fails.
        """
        self.discover()
        self.initialize()

    def shutdown(self) -> None:
        """
        Tear down all initialized modules in reverse dependency order.

        Raises:
            SpocError: If teardown of any module fails.
        """
        try:
            for module_name in reversed(self._module_order()):
                info = self._module_cache[module_name]
                self._call_hook("shutdown", module_name)
                if info.initialized and info.has_teardown():
                    info.teardown()

            self.on_shutdown()

        except (CircularDependencyError, SpocError):
            raise
        except Exception as e:
            raise SpocError(f"Error during shutdown: {e}") from e

    def clear_all(self) -> None:
        """Clear all modules from the cache (not from sys.modules)."""
        module_names = list(self._module_cache.keys())
        for name in module_names:
            self.clear(name)

    def unload_all(self) -> None:
        """
        Completely unload all cached modules from memory.

        This:
        1. Calls teardown() on all initialized modules
        2. Removes modules from the cache
        3. Removes modules from sys.modules

        Note: This is generally not recommended in production as it can cause
        unexpected behavior if other parts of the code still reference the modules.
        """
        self.shutdown()

        for name in list(self._module_cache.keys()):
            if name in sys.modules:
                del sys.modules[name]

        self._module_cache.clear()
        self._dependency_graph = {}

    def on_startup(self) -> None:
        """
        Built-in initialization hook that runs before any module initialization.

        Override this method in subclasses to provide custom initialization logic.
        """

    def on_shutdown(self) -> None:
        """
        Built-in teardown hook that runs after all module teardown operations.

        Override this method in subclasses to provide custom cleanup logic.
        """

    @staticmethod
    def simple_regex(pattern: str) -> Pattern[str]:
        """Convert a simple wildcard pattern to a regex pattern."""
        regex_pattern = pattern.replace(".", "\\.").replace("*", ".*").replace("?", ".")
        return re.compile(f"^{regex_pattern}$")

    def register_hook(
        self,
        pattern: str,
        on_startup: Callable | None = None,
        on_shutdown: Callable | None = None,
    ) -> None:
        """
        Pre-register custom initialization and teardown functions for modules.

        Hooks are instance state: two importers never share them. Each hook
        is called with the set of the module's registered component objects.

        Args:
            pattern: The fully-qualified name of the module or a pattern with wildcards.
            on_startup: Custom initialization function for this module.
            on_shutdown: Custom teardown function for this module.
        """
        if "*" in pattern or "?" in pattern:
            regex_pattern = self.simple_regex(pattern)
            self.module_hooks.pattern[pattern] = {
                "startup": HookPattern(),
                "shutdown": HookPattern(),
            }
            if on_startup is not None:
                self.module_hooks.pattern[pattern]["startup"] = HookPattern(
                    pattern=regex_pattern, method=on_startup
                )

            if on_shutdown is not None:
                self.module_hooks.pattern[pattern]["shutdown"] = HookPattern(
                    pattern=regex_pattern, method=on_shutdown
                )
        else:
            self.module_hooks.generic[pattern] = {"startup": None, "shutdown": None}
            if on_startup is not None:
                self.module_hooks.generic[pattern]["startup"] = on_startup

            if on_shutdown is not None:
                self.module_hooks.generic[pattern]["shutdown"] = on_shutdown

    def keys(self) -> list[str]:
        """All module names in the cache."""
        return list(self._module_cache.keys())
