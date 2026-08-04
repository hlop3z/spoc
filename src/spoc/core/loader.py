"""
Module loading in dependency order — the adapter over Python's import system.

The loader is deliberately **kind-blind**. It is handed a kind label with each module and
carries it back out again for hook dispatch, but it never reads or decides anything from
it. Everything the loader knows about a module is what the caller told it, which is what
keeps the registry — a pure core concern — out of here.

Absent and broken are different failures, and the distinction is contractual. A module
that does not exist is absent: whether that is an error is the caller's decision, passed
in as ``required``. A module that exists and raises while importing is broken, and that is
always an error, because the author wrote something that does not work rather than
declining to write it. The two are told apart by which module the import system says was
missing.
"""

from __future__ import annotations

import graphlib
import importlib
import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from .exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    MissingModuleError,
    SpocError,
)

logger = logging.getLogger("spoc")

#: A kind's lifecycle hooks, each called with the module's registered component objects.
type KindHooks = tuple[
    Callable[[set[Any]], Any] | None, Callable[[set[Any]], Any] | None
]


@dataclass
class LoadedModule:
    """One imported module and the labels the caller attached to it."""

    name: str
    module: ModuleType
    kind: str
    initialized: bool = False


class Loader:
    """Imports modules, orders them by dependency, and runs their lifecycle."""

    def __init__(self) -> None:
        self._modules: dict[str, LoadedModule] = {}
        self._graph: dict[str, set[str]] = {}

    def register(
        self,
        name: str,
        *,
        kind: str,
        app: str,
        dependencies: tuple[str, ...] = (),
        required: bool = True,
    ) -> ModuleType | None:
        """Import a module and record its dependencies. None if absent and optional."""
        if name in self._modules:
            return self._modules[name].module

        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name != name:
                raise  # the module exists; something it imports does not
            if required:
                raise MissingModuleError(app, kind, name) from e
            logger.debug("Skipping absent optional module %s", name)
            return None

        self._modules[name] = LoadedModule(name=name, module=module, kind=kind)
        self._graph.setdefault(name, set())
        # Edges are recorded even when the dependency is not loaded yet, or was an
        # absent optional module — ordered() filters unloaded names back out.
        for dep in dependencies:
            self._graph.setdefault(dep, set())
            self._graph[name].add(dep)
        return module

    def load_from_uri(self, uri: str) -> Any:
        """Load an attribute from a ``package.module.attribute`` reference."""
        module_path, sep, attr = uri.rpartition(".")
        if not sep:
            raise ValueError("URI must be in the form 'package.module.function'")
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise AppNotFoundError(module_path) from e
        if not hasattr(module, attr):
            raise AttributeError(f"Module '{module_path}' has no attribute '{attr}'")
        return getattr(module, attr)

    def ordered(self) -> list[LoadedModule]:
        """Loaded modules in dependency order, dependencies first."""
        try:
            order = graphlib.TopologicalSorter(self._graph).static_order()
            return [self._modules[n] for n in order if n in self._modules]
        except graphlib.CycleError as e:
            raise CircularDependencyError([str(n) for n in e.args[1]]) from e

    def __iter__(self) -> Iterator[LoadedModule]:
        return iter(self.ordered())

    def __len__(self) -> int:
        return len(self._modules)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def initialize(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], set[Any]],
    ) -> None:
        """Fire each module's startup hook, then its own ``initialize()``."""
        try:
            for entry in self.ordered():
                logger.debug("Initializing module: %s", entry.name)
                on_startup, _ = hooks.get(entry.kind, (None, None))
                if on_startup is not None:
                    on_startup(components_for(entry))
                fn = getattr(entry.module, "initialize", None)
                if callable(fn) and not entry.initialized:
                    fn()
                entry.initialized = True
        except (CircularDependencyError, SpocError):
            raise
        except Exception as e:
            raise SpocError(f"Error during startup: {e}") from e

    def shutdown(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], set[Any]],
    ) -> None:
        """Fire each module's shutdown hook, then its own ``teardown()``, in reverse."""
        try:
            for entry in reversed(self.ordered()):
                _, on_shutdown = hooks.get(entry.kind, (None, None))
                if on_shutdown is not None:
                    on_shutdown(components_for(entry))
                fn = getattr(entry.module, "teardown", None)
                if callable(fn) and entry.initialized:
                    fn()
                entry.initialized = False
        except (CircularDependencyError, SpocError):
            raise
        except Exception as e:
            raise SpocError(f"Error during shutdown: {e}") from e
