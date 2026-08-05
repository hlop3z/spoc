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

from collections import OrderedDict
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core.config import DEFAULT_MODE, load_environment, load_spoc_toml
from .core.declaration import KindSpec, as_kind_spec, discover, registrar
from .core.exceptions import ConfigurationError, SpocError, UnknownKindError
from .core.loader import KindHooks, LoadedModule, Loader
from .core.paths import eject_apps, inject_apps
from .core.registry import Component, Registry

#: Which modes cascade into which, most specific first. Development sees everything.
_MODE_CASCADE: dict[str, tuple[str, ...]] = {
    "production": ("production",),
    "staging": ("staging", "production"),
    "development": ("development", "staging", "production"),
}


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
    """The declaration point and composition root."""

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
        self.base_dir: Path | None = None
        self.config: Config | None = None
        self.plugins: dict[str, OrderedDict[str, Any]] = {}
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
        if self._started:
            raise SpocError("Framework is already started")

        base_dir = Path(base_dir)
        try:
            inject_apps(base_dir)
            self.base_dir = base_dir
            self.config = _build_config(base_dir, self.echo)
            self.plugins = self._collect_plugins()
            self._register_apps()

            for entry in self.loader.ordered():
                discover(self.registry, entry.module, entry.name)
            for callback in self._ready_callbacks:
                callback(self.registry)
            self.loader.initialize(self._hooks(), self._components_for)
        except BaseException:
            # Tear down what did come up (never-initialized modules are skipped),
            # reset to inert, then let the cause escape untouched.
            with suppress(Exception):
                self.loader.shutdown(self._hooks(), self._components_for)
            self._reset(base_dir)
            raise

        self._started = True
        return self

    def shutdown(self) -> Framework:
        """Tear down modules in reverse dependency order, then reset to pre-start state.

        After shutdown the framework is inert again — empty registry, no loaded
        modules, no injected import path — so a subsequent ``start`` is a clean boot
        rather than one layered on stale state. No-op if never started.
        """
        if not self._started:
            return self
        self.loader.shutdown(self._hooks(), self._components_for)
        assert self.base_dir is not None
        self._reset(self.base_dir)
        self._started = False
        return self

    def _reset(self, base_dir: Path) -> None:
        """Return every owned piece to its inert pre-start state."""
        eject_apps(base_dir)
        self.registry = Registry(self.kinds)
        self.loader = Loader()
        self.plugins = {}
        self.installed_apps = []
        self.config = None
        self.base_dir = None

    # ── Boot steps (private) ──────────────────────────────────────────────

    def _hooks(self) -> dict[str, KindHooks]:
        return {
            name: (spec.on_startup, spec.on_shutdown)
            for name, spec in self._specs.items()
        }

    def _components_for(self, entry: LoadedModule) -> set[Any]:
        namespace = entry.name.partition(".")[0]
        return {
            c.object
            for c in self.registry.by_kind(entry.kind)
            if c.namespace == namespace
        }

    def _collect_plugins(self) -> dict[str, OrderedDict[str, Any]]:
        assert self.config is not None
        plugins = self.config.project.get("plugins", {}) or {}
        collected: dict[str, OrderedDict[str, Any]] = {}
        for group, references in plugins.items():
            collected[group] = OrderedDict()
            for uri in references:
                if uri not in collected[group]:
                    collected[group][uri] = self.loader.load_from_uri(uri)
        return collected

    @staticmethod
    def _collect_apps(mode: str, declared: dict[str, list[str]]) -> list[str]:
        """Cascaded app list for a mode, order preserved, first wins.

        Both the active mode and every ``[spoc.apps]`` key must name a known mode:
        a typo would otherwise silently install nothing (or strand an app list).
        """
        valid = ", ".join(_MODE_CASCADE)
        if mode not in _MODE_CASCADE:
            raise ConfigurationError(f"Unknown mode {mode!r}. Valid modes: {valid}")
        for group in declared:
            if group not in _MODE_CASCADE:
                raise ConfigurationError(
                    f"Unknown mode {group!r} in [spoc.apps]. Valid modes: {valid}"
                )
        installed: list[str] = []
        seen: set[str] = set()
        for source in _MODE_CASCADE[mode]:
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
        )
        for app in app_names:
            for spec in self._specs.values():
                self.loader.register(
                    f"{app}.{spec.name}",
                    kind=spec.name,
                    app=app,
                    dependencies=tuple(f"{app}.{d}" for d in spec.depends_on),
                    required=spec.required,
                )
        self.installed_apps = app_names
