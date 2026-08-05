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
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core.config import (
    DEFAULT_MODE,
    DEFAULT_MODES,
    load_environment,
    load_spoc_toml,
)
from .core.declaration import (
    KindSpec,
    as_kind_spec,
    check_metadata,
    discover,
    registrar,
)
from .core.exceptions import ConfigurationError, SpocError, UnknownKindError
from .core.identity import to_snake_case, validate_segment
from .core.loader import KindHooks, LoadedModule, Loader
from .core.registry import Component, Registry


@dataclass(frozen=True)
class Config:
    """The ``[spoc]`` table and the environment for the active mode."""

    project: dict[str, Any]
    environment: Any


def _build_config(base_dir: Path, echo: bool = False) -> Config:
    raw = load_spoc_toml(base_dir).get("spoc", {})
    return Config(
        project=raw,
        environment=load_environment(
            base_dir, raw.get("mode", DEFAULT_MODE), echo=echo
        ),
    )


class Framework:
    """The declaration point and composition root.

    Concurrency contract: taking registration handles and decorating objects
    is thread-safe (a mark only sets an attribute on the target). Start and
    shutdown are serialized against each other and against themselves — when
    callers race to start, exactly one boot proceeds and the rest fail with
    the already-started error. Reads after a completed start need no
    coordination, because nothing writes to the registry after boot.
    """

    def __init__(self, *kinds: str | KindSpec, echo: bool = False) -> None:
        self._specs: dict[str, KindSpec] = {}
        for kind in kinds:
            spec = as_kind_spec(kind)
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

    def kind(self, kind: str) -> Callable[..., Any]:
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

    def resolve(self, identifier: str) -> Component:
        """Resolve ``kind:namespace.object_name`` to its registry record."""
        return self.registry.resolve(identifier)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self, base_dir: Path | str) -> Framework:
        """Boot the project rooted at `base_dir`.

        A failed boot is rolled back: modules that came up are torn down and the
        framework returns to its inert pre-start state, so the caller can fix
        the cause and start again cleanly.
        """
        with self._transition_lock:
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

        Discovery is the same synchronous work; only hook dispatch and module
        ``initialize`` awaits. A concurrent transition is a programming error
        and fails immediately — an event loop is never parked on a lock.
        """
        if not self._transition_lock.acquire(blocking=False):
            raise SpocError("Framework lifecycle transition already in progress")
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
            self._transition_lock.release()

    def shutdown(self) -> Framework:
        """Tear down modules in reverse dependency order, then reset to pre-start state.

        Everything the kernel owns is reset — registry, module bookkeeping,
        configuration. What persists is Python's own module cache and any
        module-level state: module-level code runs at most once per process,
        and a subsequent ``start`` re-runs discovery against those cached
        modules rather than re-executing them. No-op if never started.
        """
        with self._transition_lock:
            if not self._started:
                return self
            self.loader.shutdown(self._hooks(), self._components_for)
            self._reset()
            self._started = False
            return self

    async def ashutdown(self) -> Framework:
        """Asynchronous :meth:`shutdown`: awaits coroutine hooks and teardowns."""
        if not self._transition_lock.acquire(blocking=False):
            raise SpocError("Framework lifecycle transition already in progress")
        try:
            if not self._started:
                return self
            await self.loader.ashutdown(self._hooks(), self._components_for)
            self._reset()
            self._started = False
            return self
        finally:
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

    def _components_for(self, entry: LoadedModule) -> set[Any]:
        return {
            c.object
            for c in self.registry.by_kind(entry.kind)
            if c.namespace == entry.namespace
        }

    def _register_plugins(self, project: dict[str, Any]) -> None:
        """Register config-declared references into the one flat registry.

        A ``[spoc.plugins]`` group names a declared kind — configuration is a
        second way to populate the registry, never a second registry. Identity
        follows the same grammar as discovery: the reference's top package is
        the namespace, and the attribute derives the object_name. A kind only
        plugins populate is declared ``required=False`` so apps need not
        provide a module for it.
        """
        for group, references in (project.get("plugins", {}) or {}).items():
            spec = self.spec(group)  # an undeclared group raises UnknownKindError
            for uri in references:
                obj = self.loader.load_from_uri(uri)
                module_path, _, attr = uri.rpartition(".")
                name = to_snake_case(attr)
                check_metadata(spec, name, None)
                self.registry.add(spec.name, module_path.split(".")[0], name, obj)

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
