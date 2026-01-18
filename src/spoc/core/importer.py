"""
Dynamic module importing and lifecycle management system.

This module provides a class-based API for dynamically loading modules,
caching them for efficient reuse, and managing their initialization
and teardown in dependency order.

Usage:
    from spoc.core.importer import Importer
    importer = Importer()
    module = importer.load("os")
    importer.register("myapp.models", dependencies=["myapp.utils"])
    importer.startup()
    # ... use modules ...
    importer.shutdown()

The Importer is central to the SPOC framework, enabling dynamic, dependency-aware
module management for pluggable and testable applications.
"""

from __future__ import annotations

# Standard library imports
import dataclasses
import importlib
import logging
import re
import sys
from collections.abc import Callable
from re import Pattern
from types import ModuleType
from typing import Any, ClassVar, Literal, Protocol, TypeAlias

# Local imports
from .exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    ModuleNotCachedError,
    SpocError,
)
from .singleton import SingletonMeta
from .utils import DependencyGraph

logger = logging.getLogger("spoc")


FrameworkMode: TypeAlias = Literal["strict", "loose"]


class Initializable(Protocol):
    """Protocol for objects that can be initialized."""

    def initialize(self) -> None:
        """Initialize the object."""


class Teardownable(Protocol):
    """Protocol for objects that can be torn down."""

    def teardown(self) -> None:
        """Tear down the object."""


@dataclasses.dataclass
class ModuleHooks:
    """Container for module lifecycle hooks."""

    generic: dict[str, Any] = dataclasses.field(default_factory=dict)
    pattern: dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class HookPattern:
    """Pattern matching for module hooks."""

    pattern: Pattern[str] | None = None
    method: Callable[[ModuleType], None] | None = None


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
        """
        Initialize module information.

        Args:
            name: The module name.
            module: The loaded module object.
            dependencies: List of module names this module depends on.
            initialize_func: Name of the initialization function in the module, or None.
            teardown_func: Name of the teardown function in the module, or None.
        """
        self.name = name
        self.module = module
        self.dependencies = dependencies or []
        self.initialize_func = initialize_func
        self.teardown_func = teardown_func
        self.initialized = False
        # Store references to hooks
        self.on_startup = None
        self.on_shutdown = None

    def has_initialize(self) -> bool:
        """
        Check if the module has an initialize function.

        Returns:
            True if the module has an initialize function, False otherwise.
        """
        has_init = self.initialize_func is not None and hasattr(
            self.module, self.initialize_func
        )
        logger.debug("Module %s has_initialize: %s", self.name, has_init)
        return has_init

    def has_teardown(self) -> bool:
        """
        Check if the module has a teardown function.

        Returns:
            True if the module has a teardown function, False otherwise.
        """
        has_tear = self.teardown_func is not None and hasattr(
            self.module, self.teardown_func
        )
        logger.debug("Module %s has_teardown: %s", self.name, has_tear)
        return has_tear

    def initialize(self) -> None:
        """
        Initialize the module if it has an initialize function.

        Sets the initialized flag to True after successful initialization.
        """
        if self.has_initialize() and not self.initialized:
            logger.debug("Calling initialize for module %s", self.name)
            # We've already checked that initialize_func is not None and that the attribute exists
            initialize_func = getattr(self.module, self.initialize_func or "initialize")
            initialize_func()
            self.initialized = True
            logger.debug("Module %s initialized successfully", self.name)
        else:
            logger.debug("Skipping initialization for module %s", self.name)

    def teardown(self) -> None:
        """
        Tear down the module if it has a teardown function.

        Resets the initialized flag to False after successful teardown.
        """
        if self.has_teardown() and self.initialized:
            logger.debug("Calling teardown for module %s", self.name)
            # We've already checked that teardown_func is not None and that the attribute exists
            teardown_func = getattr(self.module, self.teardown_func or "teardown")
            teardown_func()
            self.initialized = False
            logger.debug("Module %s torn down successfully", self.name)
        else:
            logger.debug("Skipping teardown for module %s", self.name)


class Importer(metaclass=SingletonMeta):
    """
    Dynamic module importer with caching and lifecycle management.

    This class provides a clean API for:
    1. Dynamically importing modules at runtime
    2. Caching modules for efficient reuse
    3. Managing module lifecycle (initialization/teardown) based on dependencies

    Time Complexity:
    - Module lookup in cache: O(1)
    - Module loading: O(1) amortized (with caching)
    - Startup/shutdown: O(N + E) where N = number of modules, E = number of dependencies

    Attributes:
        _module_cache: Internal cache of loaded modules
        _dependency_graph: Graph of module dependencies for ordered initialization/teardown
        module_hooks: Dictionary of hooks to apply to modules during lifecycle events
        on_startup_name: Name of the function to call for module initialization
        on_shutdown_name: Name of the function to call for module teardown
    """

    module_hooks: ClassVar[ModuleHooks] = ModuleHooks()

    def __init__(
        self,
        on_startup_name: str | None = "initialize",
        on_shutdown_name: str | None = "teardown",
        mode: FrameworkMode = "strict",
    ) -> None:
        """
        Initialize a new ModuleImporter instance.

        Args:
            on_startup_name: Name of the initialization function in modules, or None
            on_shutdown_name: Name of the teardown function in modules, or None
        """
        self._components: dict[str, Any] = {}
        self._module_cache: dict[str, ModuleInfo] = {}
        self._dependency_graph = DependencyGraph[str]()
        self.mode = mode
        self.on_startup_name = on_startup_name
        self.on_shutdown_name = on_shutdown_name

    def load(self, name: str) -> ModuleType | None:
        """
        Dynamically load a module by name.

        If the module is already in the cache, returns the cached module.
        Otherwise, imports the module and adds it to the cache.

        Args:
            name: The fully-qualified name of the module to load.

        Returns:
            The loaded module.

        Raises:
            ModuleNotFoundError: If the module cannot be found.
        """
        if self.has(name):
            return self._module_cache[name].module

        try:
            module = importlib.import_module(name)
            module_info = ModuleInfo(name=name, module=module)
            self._module_cache[name] = module_info
            self._dependency_graph.add_node(name)
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

        Args:
            name: The fully-qualified name of the module to register.
            dependencies: List of module names this module depends on.

        Returns:
            The loaded module.

        Raises:
            ModuleNotFoundError: If the module cannot be found.
        """
        # Load the module if not already loaded
        module = self.load(name)
        assert module is not None, f"Failed to load module {name}"

        # Update the module info with dependencies and lifecycle functions
        module_info = self._module_cache.get(name)
        if not module_info and self.mode != "strict":
            module_info = ModuleInfo(name=name, module=module)
        assert module_info is not None, f"Module {name} not found in cache"
        module_info.dependencies = dependencies or []
        module_info.on_startup = self.on_startup
        module_info.on_shutdown = self.on_shutdown

        # Add dependencies to the graph
        for dep in module_info.dependencies:
            if not self.has(dep):
                self.load(dep)
                logger.debug("Loaded dependency: %s", dep)
            self._dependency_graph.add_edge(dep, name)

        return module

    def load_from_uri(self, uri: str) -> Any:
        """Load a function from a full URI like 'package.module.func'."""
        parts = uri.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError("URI must be in the form 'package.module.function'")

        module_path, func_name = parts
        module = self.load(module_path)

        if not hasattr(module, func_name):
            raise AttributeError(
                f"Module '{module_path}' has no attribute '{func_name}'"
            )

        return getattr(module, func_name)

    def has(self, name: str) -> bool:
        """
        Check if a module is in the cache.

        Args:
            name: The name of the module to check.

        Returns:
            True if the module is in the cache, False otherwise.
        """
        return name in self._module_cache

    def get(self, name: str) -> ModuleType:
        """
        Get a module from the cache.

        Args:
            name: The name of the module to get.

        Returns:
            The cached module.

        Raises:
            ModuleNotCachedError: If the module is not in the cache.
        """
        if not self.has(name):
            raise ModuleNotCachedError(name)
        return self._module_cache[name].module

    def clear(self, name: str) -> None:
        """
        Remove a module from the cache.

        This does not unload the module from sys.modules.

        Args:
            name: The name of the module to clear.
        """
        if self.has(name):
            # Remove from our cache
            module_info = self._module_cache.pop(name)

            # Teardown if initialized
            if module_info.initialized and module_info.has_teardown():
                module_info.teardown()

    def _get_module_objects(self, module_name: str) -> set[Any]:
        """Return `spoc` attributes of a module."""
        module: ModuleType = self.get(module_name)
        objects = [
            n for n in dir(module) if not n.startswith("_") and not n.endswith("_")
        ]
        items = set()
        for name in objects:
            current = getattr(module, name)
            if hasattr(current, "__spoc__"):
                type_name = getattr(current, "__spoc__").metadata.get("type")
                pkg, mod = module_name.rsplit(".", 1)
                if mod not in self._components:
                    self._components[mod] = {}
                if type_name == mod:
                    items.add(current)
                    self._components[mod][f"{pkg}.{name}"] = current
        return items

    def _call_hook(
        self, hook_type: Literal["startup", "shutdown"], module_name: str
    ) -> None:
        """
        Call a hook for a module.

        Args:
            hook_type: The type of hook to call.
            module_name: The name of the module to call the hook for.
        """
        hook = self.module_hooks.generic.get(module_name)
        if hook:
            instance = self._get_module_objects(module_name)
            hook.get(hook_type)(instance)
        else:
            for current in self.module_hooks.pattern.values():
                if current.get(hook_type).pattern.fullmatch(module_name):
                    instance = self._get_module_objects(module_name)
                    current.get(hook_type).method(instance)

    def startup(self) -> None:
        """
        Initialize all registered modules in dependency order.

        This ensures that modules are initialized only after their
        dependencies have been initialized.

        Raises:
            CircularDependencyError: If there are circular dependencies.
            LifecycleError: If initialization of any module fails.
        """
        try:
            self.on_startup()

            module_order = self._dependency_graph.topological_sort()
            logger.debug("Module initialization order: %s", module_order)

            for module_name in module_order:
                if module_name in self._module_cache:
                    logger.debug("Initializing module: %s", module_name)
                    self._call_hook("startup", module_name)
                    self._module_cache[module_name].initialize()

        except CircularDependencyError:
            raise
        except Exception as e:
            raise SpocError(f"Error during startup: {e}") from e

    def shutdown(self) -> None:
        """
        Tear down all initialized modules in reverse dependency order.

        This ensures that modules are torn down only after all modules
        that depend on them have been torn down.

        Raises:
            LifecycleError: If teardown of any module fails.
        """
        try:
            reversed_graph = self._dependency_graph.reversed()
            module_order = reversed_graph.topological_sort()

            for module_name in module_order:
                if module_name in self._module_cache:
                    info = self._module_cache[module_name]
                    self._call_hook("shutdown", module_name)
                    if info.initialized and info.has_teardown():
                        info.teardown()

            self.on_shutdown()

        except Exception as e:
            raise SpocError(f"Error during shutdown: {e}") from e

    def clear_all(self) -> None:
        """
        Clear all modules from the cache.

        This does not unload modules from sys.modules.
        """
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
        self._dependency_graph = DependencyGraph[str]()

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
        """
        Convert a simple pattern to a regex pattern.
        """
        regex_pattern = pattern.replace(".", "\\.").replace("*", ".*").replace("?", ".")
        return re.compile(f"^{regex_pattern}$")

    @classmethod
    def register_hook(
        cls,
        pattern: str,
        on_startup: Callable | None = None,
        on_shutdown: Callable | None = None,
    ) -> None:
        """
        Pre-register custom initialization and teardown functions for modules.

        These hooks will be attached to the module when it's loaded, overriding any default hooks.

        Args:
            pattern: The fully-qualified name of the module or a pattern with wildcards.
            on_startup: Custom initialization function for this module.
            on_shutdown: Custom teardown function for this module.
        """

        if "*" in pattern or "?" in pattern:
            regex_pattern = cls.simple_regex(pattern)
            cls.module_hooks.pattern[pattern] = {
                "startup": HookPattern(),
                "shutdown": HookPattern(),
            }
            if on_startup is not None:
                cls.module_hooks.pattern[pattern]["startup"] = HookPattern(
                    pattern=regex_pattern, method=on_startup
                )

            if on_shutdown is not None:
                cls.module_hooks.pattern[pattern]["shutdown"] = HookPattern(
                    pattern=regex_pattern, method=on_shutdown
                )
        else:
            cls.module_hooks.generic[pattern] = {"startup": {}, "shutdown": {}}
            if on_startup is not None:
                cls.module_hooks.generic[pattern]["startup"] = on_startup

            if on_shutdown is not None:
                cls.module_hooks.generic[pattern]["shutdown"] = on_shutdown

    def keys(self) -> list[str]:
        """
        Get a list of all module names in the cache.
        """
        return list(self._module_cache.keys())

    @property
    def components(self) -> dict[str, dict[str, Any]]:
        """
        Get a dictionary of all components and their instances.
        """
        return self._components
