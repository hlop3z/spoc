"""
The framework object — the single declaration point and the composition root.

Everything the kernel knows is stated once, here: the closed kind set as a sequence of
:class:`~spoc.core.declaration.KindSpec` records, and the ready callbacks. Construction is
inert — no filesystem, no imports, no process-global mutation — so app modules can take
registration handles at import time and the framework only boots when ``start(base_dir)``
says so.

This is the only module that wires the pieces together. The registry, the loader, and the
configuration adapter are all owned here and none of them knows about the others: the
registry never imports anything, the loader never sees a registry, and the config adapter
only reads files. Dependencies point inward, and this is where they meet.

    import spoc

    framework = spoc.Framework("models", spoc.KindSpec("views", depends_on=("models",)))
    model = framework.kind("models")

    @model
    class Post: ...           # → models:blog.post

    framework.start(Path("."))
    record = framework.resolve("models:blog.post")

The kernel describes — it never executes. Resolution is a pure lookup; invocation belongs
to the surfaces built on top.
"""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core.config import (
    DEFAULT_MODE,
    DEFAULT_MODES,
    load_environment,
    load_spoc_toml,
)
from .core.declaration import (
    KindHandle,
    KindSpec,
    as_kind_spec,
    discover,
    registrar,
)
from .core.exceptions import (
    ComponentShapeError,
    ConfigurationError,
    SpocError,
    UnknownKindError,
)
from .core.identity import to_snake_case, validate_segment
from .core.loader import KindHooks, LoadedModule, Loader
from .core.registry import Component, Registry


@dataclass(frozen=True)
class Config:
    """The ``[spoc]`` table, the active mode's environment, and the app's own tables.

    ``tables`` holds every top-level table in ``spoc.toml`` other than ``[spoc]``,
    as parsed — the kernel neither validates nor reads them. Validating them is the
    application's job, through whatever schema tool it adopts.
    """

    project: dict[str, Any]
    environment: Any
    tables: dict[str, Any] = field(default_factory=dict)


def _shape_of(obj: Any) -> str:
    """Name a component's shape in the vocabulary typed access reports.

    The three shapes are exhaustive and ordered: a class is constructible even
    though it is also callable, so the checks cannot be reversed.
    """
    if isinstance(obj, type):
        return "a constructible object"
    if callable(obj):
        return "a callable"
    return "a value"


def _build_config(base_dir: Path, echo: bool = False) -> Config:
    loaded = load_spoc_toml(base_dir, echo=echo)
    spoc_table = loaded.get("spoc", {})
    return Config(
        project=spoc_table,
        environment=load_environment(
            base_dir, spoc_table.get("mode", DEFAULT_MODE), echo=echo
        ),
        tables={k: v for k, v in loaded.items() if k != "spoc"},
    )


class Framework:
    """The declaration point and composition root.

    Concurrency contract: taking registration handles and decorating objects
    is thread-safe (a mark only sets an attribute on the target). Start and
    shutdown are serialized against each other and against themselves — when
    callers race to start, exactly one boot proceeds and the rest fail with
    the already-started error. Reads after a completed start need no
    coordination, because nothing writes to the registry after boot.

    A transition invoked from *inside* a transition — a ready callback or
    lifecycle hook calling ``start`` or ``shutdown`` — fails immediately
    rather than deadlocking on the non-reentrant lock. The transition is
    mid-flight and its state is half-built, so there is no correct thing for
    the inner call to do.
    """

    def __init__(self, *kinds: str | KindSpec, echo: bool = False) -> None:
        self._specs: dict[str, KindSpec] = {}
        for kind in kinds:
            spec = as_kind_spec(kind)
            if spec.name in self._specs:
                # Last-wins would let a second declaration silently replace the
                # first's dependencies, optionality, and hooks.
                raise ConfigurationError(
                    f"Kind {spec.name!r} is declared more than once. "
                    "Each kind is declared exactly once, on one KindSpec"
                )
            self._specs[spec.name] = spec
        for spec in self._specs.values():
            for dep in spec.depends_on:
                if dep not in self._specs:
                    raise UnknownKindError(dep, self.kinds)

        self.echo = echo
        self.registry = Registry(self.kinds)
        self.loader = Loader()
        self._ready_callbacks: list[Callable[[Registry], Any]] = []
        self._started = False
        self._transition_lock = threading.Lock()
        #: Thread currently inside a lifecycle transition, so a reentrant call
        #: from lifecycle code can be told apart from a racing caller.
        self._transition_owner: int | None = None
        self.base_dir: Path | None = None
        self.config: Config | None = None
        self.installed_apps: list[str] = []

    # ── Declaration surface ───────────────────────────────────────────────

    @property
    def kinds(self) -> tuple[str, ...]:
        """The declared kind set (closed; fixed at construction)."""
        return tuple(self._specs)

    def spec(self, kind: str) -> KindSpec:
        """The full declaration for one kind."""
        if kind not in self._specs:
            raise UnknownKindError(kind, self.kinds)
        return self._specs[kind]

    def kind(self, kind: str) -> KindHandle:
        """The registration handle for a declared kind."""
        return registrar(self.spec(kind))

    def on_ready(
        self, callback: Callable[[Registry], Any]
    ) -> Callable[[Registry], Any]:
        """Register a finalize callback, fired once after discovery completes."""
        self._ready_callbacks.append(callback)
        return callback

    # ── Reads ─────────────────────────────────────────────────────────────

    @property
    def started(self) -> bool:
        """True once ``start`` has completed successfully."""
        return self._started

    def resolve(self, identifier: str) -> Component[Any]:
        """Resolve ``kind:namespace.object_name`` to its registry record."""
        return self.registry.resolve(identifier)

    def resolve_type[T](self, identifier: str, contract: type[T]) -> type[T]:
        """Resolve a constructible component under a caller-owned contract.

        `contract` is read by the type checker, not by this method: it names the
        static type the caller expects and never reaches the registry. Pointing
        it at a ``Protocol`` the *calling* app declares is what keeps typed
        access from re-coupling the two apps — the caller states the shape it
        needs instead of importing the module that provides it.

        Only shape is checked here; see :meth:`resolve_object` for the rest of
        the contract this pair shares.
        """
        obj = self.registry.resolve(identifier).object
        if not isinstance(obj, type):
            raise ComponentShapeError(
                identifier, "a constructible object", _shape_of(obj)
            )
        return obj

    def resolve_object[T](self, identifier: str, contract: type[T]) -> T:
        """Resolve a value or callable component under a caller-owned contract.

        The counterpart to :meth:`resolve_type`, and the pair is exhaustive
        because ``type[T]`` versus ``T`` is the only distinction the type system
        forces. A callable is returned uninvoked: the kernel describes, and
        typed access is still a pure lookup.

        Neither accessor inspects the object's members. Whether it structurally
        satisfies `contract` is a static question, answered where the contract
        is visible; re-answering it at runtime would duplicate a known fact and
        put a validation engine in the kernel.
        """
        obj = self.registry.resolve(identifier).object
        if isinstance(obj, type):
            raise ComponentShapeError(
                identifier, "a value or a callable", _shape_of(obj)
            )
        return obj

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def _refuse_reentry(self, label: str) -> None:
        """Refuse a transition called from inside one already on this thread."""
        if self._transition_owner == threading.get_ident():
            raise SpocError(
                f"{label} was called from inside a lifecycle transition already "
                "running on this thread. A ready callback, lifecycle hook, or "
                "module initializer cannot start or shut down the framework "
                "that is booting it"
            )

    @contextmanager
    def _transition(self, label: str) -> Iterator[None]:
        """Hold the transition lock, recording the owning thread."""
        self._refuse_reentry(label)
        with self._transition_lock:
            self._transition_owner = threading.get_ident()
            try:
                yield
            finally:
                self._transition_owner = None

    def start(self, base_dir: Path | str) -> Framework:
        """Boot the project rooted at `base_dir`.

        A failed boot is rolled back: modules that came up are torn down and the
        framework returns to its inert pre-start state, so the caller can fix
        the cause and start again cleanly.
        """
        with self._transition("start()"):
            if self._started:
                raise SpocError("Framework is already started")

            base_dir = Path(base_dir)
            try:
                self._boot_discovery(base_dir)
                self.loader.initialize(self._hooks(), self._components_for)
            except BaseException:
                # Tear down what did come up (never-initialized modules are
                # skipped), reset to inert, then let the cause escape untouched.
                with suppress(Exception):
                    self.loader.shutdown(self._hooks(), self._components_for)
                self._reset()
                raise

            self._started = True
            return self

    async def astart(self, base_dir: Path | str) -> Framework:
        """Asynchronous :meth:`start`: awaits coroutine hooks and module code.

        Discovery is the same synchronous work — configuration reads and module
        imports run on the calling thread and do not yield to the event loop.
        Only hook dispatch and module ``initialize`` awaits. A concurrent
        transition is a programming error and fails immediately — an event loop
        is never parked on a lock.
        """
        self._refuse_reentry("astart()")
        if not self._transition_lock.acquire(blocking=False):
            raise SpocError("Framework lifecycle transition already in progress")
        self._transition_owner = threading.get_ident()
        try:
            if self._started:
                raise SpocError("Framework is already started")

            base_dir = Path(base_dir)
            try:
                self._boot_discovery(base_dir)
                await self.loader.ainitialize(self._hooks(), self._components_for)
            except BaseException:
                with suppress(Exception):
                    await self.loader.ashutdown(self._hooks(), self._components_for)
                self._reset()
                raise

            self._started = True
            return self
        finally:
            self._transition_owner = None
            self._transition_lock.release()

    def shutdown(self) -> Framework:
        """Tear down modules in reverse dependency order, then reset to pre-start state.

        Everything the kernel owns is reset — registry, module bookkeeping,
        configuration. What persists is Python's own module cache and any
        module-level state: module-level code runs at most once per process,
        and a subsequent ``start`` re-runs discovery against those cached
        modules rather than re-executing them. No-op if never started.
        """
        with self._transition("shutdown()"):
            if not self._started:
                return self
            self.loader.shutdown(self._hooks(), self._components_for)
            self._reset()
            self._started = False
            return self

    async def ashutdown(self) -> Framework:
        """Asynchronous :meth:`shutdown`: awaits coroutine hooks and teardowns."""
        self._refuse_reentry("ashutdown()")
        if not self._transition_lock.acquire(blocking=False):
            raise SpocError("Framework lifecycle transition already in progress")
        self._transition_owner = threading.get_ident()
        try:
            if not self._started:
                return self
            await self.loader.ashutdown(self._hooks(), self._components_for)
            self._reset()
            self._started = False
            return self
        finally:
            self._transition_owner = None
            self._transition_lock.release()

    def _reset(self) -> None:
        """Return every owned piece to its inert pre-start state."""
        self.registry = Registry(self.kinds)
        self.loader = Loader()
        self.installed_apps = []
        self.config = None
        self.base_dir = None

    # ── Boot steps (private) ──────────────────────────────────────────────

    def _boot_discovery(self, base_dir: Path) -> None:
        """The synchronous boot phases shared by both lifecycle paths:
        configuration, app registration, discovery, and ready callbacks."""
        # A failed boot's contract is "fix the cause and start again" — the
        # fix may be a file created since the last import attempt, which the
        # import system's directory caches would otherwise still hide.
        importlib.invalidate_caches()
        self.base_dir = base_dir
        self.config = _build_config(base_dir, self.echo)
        self._register_plugins(self.config.project)
        self._register_apps()

        for entry in self.loader.ordered():
            discover(self.registry, entry.module, entry.name, entry.namespace)
        for callback in self._ready_callbacks:
            callback(self.registry)

    def _hooks(self) -> dict[str, KindHooks]:
        return {
            name: (spec.on_startup, spec.on_shutdown)
            for name, spec in self._specs.items()
        }

    def _components_for(self, entry: LoadedModule) -> tuple[Any, ...]:
        # by_kind enumerates in canonical-identifier order; the tuple hands
        # hooks that same deterministic, immutable view.
        return tuple(
            c.object
            for c in self.registry.by_kind(entry.kind)
            if c.namespace == entry.namespace
        )

    def _register_plugins(self, project: dict[str, Any]) -> None:
        """Register config-declared references into the one flat registry.

        A ``[spoc.plugins]`` group names a declared kind — configuration is a
        second way to populate the registry, never a second registry. Identity
        follows the same grammar as discovery: a reference reads
        ``<app_path>.<module>.<attribute>``, so the segment before the module
        (the app path's final segment) is the namespace — a top-level module
        is its own namespace — and the attribute derives the object_name. A
        kind only plugins populate is declared ``required=False`` so apps
        need not provide a module for it.

        A configured reference is a name in a file — there is nowhere for it to
        carry metadata — so a kind that states a metadata contract cannot be
        populated this way, and says so rather than reporting a contract
        violation the author has no way to satisfy.
        """
        for group, references in (project.get("plugins", {}) or {}).items():
            spec = self.spec(group)  # an undeclared group raises UnknownKindError
            if spec.metadata is not None and references:
                raise ConfigurationError(
                    f"Kind {spec.name!r} declares the metadata contract "
                    f"{spec.metadata.__name__}, which a [spoc.plugins] entry "
                    "cannot supply. Register its components from an app module, "
                    "where metadata is passed at declaration"
                )
            for uri in references:
                obj = self.loader.load_from_uri(uri)
                module_path, _, attr = uri.rpartition(".")
                segments = module_path.split(".")
                namespace = validate_segment(
                    "namespace", segments[-2] if len(segments) > 1 else segments[-1]
                )
                object_name = to_snake_case(attr)
                self.registry.add(spec.name, namespace, object_name, obj)

    @staticmethod
    def _collect_apps(
        mode: str,
        declared: dict[str, list[str]],
        modes: dict[str, list[str]],
    ) -> list[str]:
        """Cascaded app list for a mode, order preserved, first wins.

        The mode set itself is configuration (``[spoc.modes]``, merged over the
        default triple). The active mode, every ``[spoc.apps]`` key, and every
        cascade entry must name a mode in that effective set: a typo would
        otherwise silently install nothing (or strand an app list).
        """
        valid = ", ".join(modes)
        if mode not in modes:
            raise ConfigurationError(f"Unknown mode {mode!r}. Valid modes: {valid}")
        for group in declared:
            if group not in modes:
                raise ConfigurationError(
                    f"Unknown mode {group!r} in [spoc.apps]. Valid modes: {valid}"
                )
        for name, cascade in modes.items():
            for entry in cascade:
                if entry not in modes:
                    raise ConfigurationError(
                        f"Unknown mode {entry!r} in the cascade of "
                        f"[spoc.modes.{name}]. Valid modes: {valid}"
                    )
        installed: list[str] = []
        seen: set[str] = set()
        for source in modes[mode]:
            for app in declared.get(source, []):
                if app not in seen:
                    seen.add(app)
                    installed.append(app)
        return installed

    def _register_apps(self) -> None:
        assert self.config is not None
        app_names = self._collect_apps(
            self.config.project.get("mode", DEFAULT_MODE),
            self.config.project.get("apps", {}),
            self.config.project.get("modes", DEFAULT_MODES),
        )
        for app in app_names:
            # An app entry is a dotted module path imported exactly as written;
            # its final segment is the namespace and must satisfy the grammar.
            namespace = validate_segment("namespace", app.rpartition(".")[2])
            for spec in self._specs.values():
                self.loader.register(
                    f"{app}.{spec.name}",
                    kind=spec.name,
                    app=app,
                    namespace=namespace,
                    dependencies=tuple(f"{app}.{d}" for d in spec.depends_on),
                    required=spec.required,
                )
        self.installed_apps = app_names
