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
import inspect
import logging
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from .exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    MissingModuleError,
    SpocError,
    UnresolvedReferenceError,
)

logger = logging.getLogger(__name__)

#: A kind's lifecycle hooks, each called with the module's registered component
#: objects as an immutable sequence in registration order.
type KindHooks = tuple[
    Callable[[Sequence[Any]], Any] | None, Callable[[Sequence[Any]], Any] | None
]

#: One unit of lifecycle work: the app-authored callable and the arguments it
#: takes. The callable is carried unwrapped so a coroutine function is still
#: recognizable as one — wrapping it in a thunk would hide that from the
#: synchronous path's refusal.
type _Step = tuple[Callable[..., Any], tuple[Any, ...]]


@dataclass
class LoadedModule:
    """One imported module and the labels the caller attached to it."""

    name: str
    module: ModuleType
    kind: str
    namespace: str = ""
    #: Where this module sits in the load order: the rank of its kind in the
    #: declared inter-kind dependency order, then the position of its app in the
    #: effective installed-app list. The loader carries this without interpreting
    #: it, exactly as it carries `kind` — the framework owns what the numbers mean.
    position: tuple[int, int] = (0, 0)
    #: The module came through the initialize phase — whether or not it defined
    #: an ``initialize()`` of its own — so its ``teardown()`` is owed. A module
    #: that defines neither is still flagged, which costs nothing: shutdown looks
    #: for a ``teardown()`` and finds none.
    initialized: bool = False
    #: The startup phase completed for this module — the kind's startup hook ran,
    #: or there was none to run — so the shutdown hook is owed. Tracked apart
    #: from `initialized` because a module whose own ``initialize()`` raises has
    #: still been through startup, and rollback must pair the two halves.
    started: bool = False


class Loader:
    """Imports modules, walks them in a stated order, and runs their lifecycle.

    The order is the caller's, carried on each module as `position`; the loader
    ranks nothing itself. What it owns is the refusal: the dependency edges it
    records exist so a cycle is caught, not so an order can be inferred from them.
    A caller that states no position gets registration order.
    """

    def __init__(self) -> None:
        self._modules: dict[str, LoadedModule] = {}
        self._graph: dict[str, set[str]] = {}

    def register(
        self,
        name: str,
        *,
        kind: str,
        app: str,
        namespace: str = "",
        dependencies: tuple[str, ...] = (),
        required: bool = True,
        position: tuple[int, int] = (0, 0),
    ) -> ModuleType | None:
        """Import a module and record its dependencies. None if absent and optional.

        The module is imported exactly as named, through the normal import
        system — the loader never alters the import environment to make a
        name resolvable.
        """
        if name in self._modules:
            existing = self._modules[name]
            if (kind, namespace) != (existing.kind, existing.namespace) or set(
                dependencies
            ) != self._graph.get(name, set()):
                raise SpocError(
                    f"Module {name!r} is already registered with different "
                    "labels or dependencies. Registering it again would "
                    "silently discard the new edges",
                    name,
                )
            return existing.module

        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError as e:
            absent = e.name is not None and (
                e.name == name or name.startswith(e.name + ".")
            )
            if not absent:
                raise  # the module exists; something it imports does not
            if e.name != name:
                # The app package itself is missing, not just this kind's module.
                # A declared app that does not exist is always an error: `required`
                # governs whether an existing app may omit a kind, nothing more.
                raise AppNotFoundError(app) from e
            if required:
                raise MissingModuleError(app, kind, name) from e
            logger.debug("Skipping absent optional module %s", name)
            return None

        self._modules[name] = LoadedModule(
            name=name,
            module=module,
            kind=kind,
            namespace=namespace,
            position=position,
        )
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
        # Every segment must be non-empty. An empty or dot-leading module path makes
        # importlib raise its own ValueError/TypeError before this method's
        # ModuleNotFoundError handler can see it, which would escape the error family.
        if not sep or not attr or not all(module_path.split(".")):
            raise UnresolvedReferenceError(
                uri, "expected the form 'package.module.attribute'"
            )
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            if e.name is not None and (
                e.name == module_path or module_path.startswith(e.name + ".")
            ):
                raise AppNotFoundError(module_path) from e
            raise  # the module exists; something it imports does not
        if not hasattr(module, attr):
            raise UnresolvedReferenceError(
                uri, f"module {module_path!r} has no attribute {attr!r}"
            )
        return getattr(module, attr)

    def ordered(self) -> list[LoadedModule]:
        """Loaded modules in load order: kind phase first, app position within it.

        The order is the framework's, stated by each module's `position`, rather
        than a library's. `graphlib` is kept for the one thing only it does here —
        refusing a dependency cycle — because sorting by a key cannot notice that
        the graph is not a DAG. Sorting an already-total key also means an absent
        optional module cannot pull anything into an earlier phase, which reading
        depth out of this graph would allow: the dependent's registration puts the
        missing name back as a node with no predecessors.
        """
        try:
            graphlib.TopologicalSorter(self._graph).prepare()
        except graphlib.CycleError as e:
            raise CircularDependencyError([str(n) for n in e.args[1]]) from e
        return sorted(self._modules.values(), key=lambda entry: entry.position)

    def __iter__(self) -> Iterator[LoadedModule]:
        return iter(self.ordered())

    def __len__(self) -> int:
        return len(self._modules)

    # ── Lifecycle ─────────────────────────────────────────────────────────
    #
    # Each phase is described once, as a generator of the steps it must run in
    # order which owns the flag bookkeeping between them. The synchronous and
    # asynchronous drivers consume that one description and differ only in
    # whether they call or await, so the order, the hook dispatch, and the
    # bookkeeping cannot drift apart. They previously could, and had: both
    # initialize paths logged per module while neither shutdown path logged.
    #
    # A flag is set only once the generator resumes, which is after the driver
    # has run the step — so a hook or module function that raises leaves its own
    # flag unset, and shutdown tears down exactly what came up.
    #
    # Both phases share one error contract: a failure raised by a hook or a
    # module's own lifecycle function is the app author's, and propagates
    # untouched. The kernel's own refusal — a coroutine the synchronous path
    # cannot run — is a precondition checked before any step runs.

    def _startup_steps(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], Sequence[Any]],
    ) -> Iterator[_Step]:
        """The startup phase in load order: each kind's hook, then the module's own."""
        for entry in self.ordered():
            logger.debug("Initializing module: %s", entry.name)
            on_startup, _ = hooks.get(entry.kind, (None, None))
            if on_startup is not None:
                yield on_startup, (components_for(entry),)
            entry.started = True
            fn = getattr(entry.module, "initialize", None)
            if callable(fn) and not entry.initialized:
                yield fn, ()
            entry.initialized = True

    def _shutdown_steps(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], Sequence[Any]],
    ) -> Iterator[_Step]:
        """The shutdown phase reversed: each kind's hook, then the module's teardown.

        What never came up is not torn down, and the two halves are tracked
        separately: a module whose own ``initialize()`` raised after its kind's
        startup hook fired still gets the paired shutdown hook, but not a
        ``teardown()`` for an initialize that never completed.
        """
        for entry in reversed(self.ordered()):
            logger.debug("Tearing down module: %s", entry.name)
            if entry.started:
                _, on_shutdown = hooks.get(entry.kind, (None, None))
                if on_shutdown is not None:
                    yield on_shutdown, (components_for(entry),)
                entry.started = False
            if entry.initialized:
                fn = getattr(entry.module, "teardown", None)
                if callable(fn):
                    yield fn, ()
                entry.initialized = False

    def _coroutines_in(
        self, hooks: dict[str, KindHooks], *, startup: bool
    ) -> list[str]:
        """Name every coroutine callable the named phase would have to run.

        Reported together rather than one at a time: an author who declared two
        of them should learn about both from one run.
        """
        offenders: list[str] = []
        for entry in self.ordered():
            on_startup, on_shutdown = hooks.get(entry.kind, (None, None))
            hook = on_startup if startup else on_shutdown
            if hook is not None and inspect.iscoroutinefunction(hook):
                label = "startup" if startup else "shutdown"
                offenders.append(f"{label} hook for kind {entry.kind!r}")
            attr = "initialize" if startup else "teardown"
            fn = getattr(entry.module, attr, None)
            if callable(fn) and inspect.iscoroutinefunction(fn):
                offenders.append(f"{entry.name}.{attr}")
        return list(dict.fromkeys(offenders))

    @staticmethod
    def _refuse_coroutines(offenders: Sequence[str]) -> None:
        """Refuse before any step has run, so no side effect precedes the refusal."""
        if not offenders:
            return
        subject = ", ".join(offenders)
        if len(offenders) == 1:
            raise SpocError(
                f"{subject} is a coroutine function; the synchronous lifecycle "
                "cannot run it — use astart()/ashutdown() to await it"
            )
        raise SpocError(
            f"{subject} are coroutine functions; the synchronous lifecycle "
            "cannot run them — use astart()/ashutdown() to await them"
        )

    def initialize(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], Sequence[Any]],
    ) -> None:
        """Fire each module's startup hook, then its own ``initialize()``."""
        self._refuse_coroutines(self._coroutines_in(hooks, startup=True))
        for call, args in self._startup_steps(hooks, components_for):
            call(*args)

    async def ainitialize(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], Sequence[Any]],
    ) -> None:
        """Asynchronous :meth:`initialize`: awaits coroutine hooks and modules."""
        for call, args in self._startup_steps(hooks, components_for):
            result = call(*args)
            if inspect.isawaitable(result):
                await result

    def shutdown(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], Sequence[Any]],
    ) -> None:
        """Fire each module's shutdown hook, then its own ``teardown()``, in reverse."""
        self._refuse_coroutines(self._coroutines_in(hooks, startup=False))
        for call, args in self._shutdown_steps(hooks, components_for):
            call(*args)

    async def ashutdown(
        self,
        hooks: dict[str, KindHooks],
        components_for: Callable[[LoadedModule], Sequence[Any]],
    ) -> None:
        """Asynchronous :meth:`shutdown`: awaits coroutine hooks and teardowns."""
        for call, args in self._shutdown_steps(hooks, components_for):
            result = call(*args)
            if inspect.isawaitable(result):
                await result
