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

import graphlib
import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

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
    CircularDependencyError,
    ComponentShapeError,
    ConfigurationError,
    SpocError,
    UnknownKindError,
)
from .core.identity import to_snake_case, validate_segment
from .core.loader import KindHooks, LoadedModule, Loader
from .core.navigation import navigator
from .core.registry import Component, Registry
from .core.shape import shape_prose
from .core.transition import TransitionGate

logger = logging.getLogger(__name__)

#: Logged when a rollback fails while unwinding a failed boot. The boot's own
#: failure is the one the caller must act on, so this one is recorded rather
#: than raised — but it is never discarded silently.
_ROLLBACK_FAILED = (
    "Rollback failed while unwinding a failed boot; the framework was still "
    "returned to its inert state, and the boot's own failure is the one raised"
)


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


#: Separates an app's module path from an explicitly stated namespace. Python's
#: own word for rebinding a name to avoid a clash, so there is nothing new to
#: learn — and it does not overload ``:``, which already means "attribute" in
#: this project's ``module.path:attribute`` references. The surrounding spaces
#: are what make it unambiguous: a dotted module path cannot contain whitespace,
#: so a package named ``aspect`` or ``last`` is unaffected.
_NAMESPACE_ALIAS = " as "


@dataclass(frozen=True)
class _AppEntry:
    """One `[spoc.apps]` entry, split into what it imports and what it claims."""

    path: str
    namespace: str


def _parse_app_entry(entry: str) -> _AppEntry:
    """Split a declared app entry into its module path and its namespace.

    ``"apps.shop"`` derives the namespace from the final path segment;
    ``"vendor.shop as vendor_shop"`` states it. The stated form exists so two
    apps whose folders happen to share a name can coexist without renaming a
    package the author may not control — a vendored tree, a third-party
    distribution.

    Either way the namespace goes through :func:`validate_segment`, so derived
    and stated names are held to the one grammar.
    """
    head, separator, tail = entry.partition(_NAMESPACE_ALIAS)
    path = head.strip()
    stated = tail.strip()
    # Neither a module path nor a namespace can contain whitespace, so interior
    # space is what catches every malformed shape at once: a bare `as`, a
    # missing side, a second clause.
    contains_space = any(part.split() != [part] for part in (path, stated) if part)
    if not path or contains_space or (separator and not stated):
        raise ConfigurationError(
            f"Malformed app entry {entry!r}. Expected a dotted module path, "
            "optionally followed by ' as <namespace>'"
        )
    namespace = stated if separator else path.rpartition(".")[2]
    return _AppEntry(path=path, namespace=validate_segment("namespace", namespace))


def _claim(owners: dict[str, str], namespace: str, package: str) -> None:
    """Record `package` as the owner of `namespace`, or refuse the contest.

    A namespace names one place. Because it derives from a path's *final*
    segment, two packages under different parents collide on that segment
    without either author doing anything unusual — and the merge is silent
    until they also happen to declare the same object name, at which point the
    error names a third place entirely.
    """
    owner = owners.setdefault(namespace, package)
    if owner != package:
        raise ConfigurationError(
            f"Namespace {namespace!r} is claimed by two packages: {owner!r} and "
            f"{package!r}. A namespace names one place, so one of them must "
            "claim a different one: give that app an 'as' clause in "
            '[spoc.apps], as in "pkg.thing as other_name"'
        )


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
    the already-started error. Reads between a completed start and a shutdown
    need no coordination, because nothing writes to the registry in that window.

    A transition is a window with an inside and an outside. Code the transition
    itself invoked — a ready callback, a lifecycle hook, a module's
    ``initialize`` or ``teardown``, anything they call in turn — is inside it and
    resolves normally, which is what lets teardown reach the components it exists
    to tear down. Every other caller is outside it and is refused with
    :class:`~spoc.FrameworkTransitioningError` for the whole window. Refusing is
    the honest answer: during a transition the registry is being populated app by
    app, or has already been replaced, so serving such a read would either report
    a typo the caller never made or hand back a component whose teardown has run.

    Draining in-flight readers is *not* this object's job, and the refusal is not
    a substitute for one. Whoever admitted the work orders it — a served
    application gets that from its server, which finishes in-flight work before
    shutting the application down. A component resolved before a transition and
    used after it remains the caller's responsibility; the framework never
    observes the use of what it returned.

    A transition invoked from *inside* a transition — a ready callback or
    lifecycle hook calling ``start`` or ``shutdown`` — fails immediately
    rather than deadlocking on the non-reentrant lock. The transition is
    mid-flight and its state is half-built, so there is no correct thing for
    the inner call to do. Inside is decided by the same test a read gets, so a
    caller the transition never invoked is reported as concurrent instead, and
    told it may retry once the window closes — the one remedy that works for it
    and never works for genuine reentry.
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
        #: Serializes this framework's transitions and answers who is inside one.
        #: Built here and nowhere else: membership is keyed by the gate, so a
        #: second gate on one framework would silently split it in two.
        self._transitions = TransitionGate()
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
        self._transitions.refuse_racing_read(identifier)
        return self.registry.resolve(identifier)

    @property
    def objects(self) -> Any:
        """The registry navigated by grammar segment: ``objects.models.shop.product``.

        The same records :meth:`resolve` returns, reached by walking the three
        facets of the identifier instead of spelling it as a string. Use this
        when the identifier is known as you write the code — a generated stub
        describes every step, so an editor completes each segment and a checker
        knows the component's type. Use :meth:`resolve` when the identifier is
        built at runtime, which no attribute path can express.

        A property, not an attribute set in ``__init__``: the walk reads the
        registry when asked, so there is nothing to keep in sync and no cost for
        a project that never navigates. Typed as ``Any`` because the accurate
        type is the generated stub's description of *this* project's registry.
        """
        self._transitions.refuse_racing_read("objects")
        return navigator(self.registry)

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
        self._transitions.refuse_racing_read(identifier)
        obj = self.registry.resolve(identifier).object
        if not isinstance(obj, type):
            raise ComponentShapeError(
                identifier, "a constructible object", shape_prose(obj)
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
        self._transitions.refuse_racing_read(identifier)
        obj = self.registry.resolve(identifier).object
        if isinstance(obj, type):
            raise ComponentShapeError(
                identifier, "a value or a callable", shape_prose(obj)
            )
        # The registry holds components as `Any` by design, and this accessor's
        # contract is that `contract` is checked statically at the call site rather
        # than re-answered here — the docstring above says so. The cast is where
        # that documented division lands in the type system.
        return cast("T", obj)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self, base_dir: Path | str) -> Framework:
        """Boot the project rooted at `base_dir`.

        A failed boot is rolled back: modules that came up are torn down and the
        framework returns to its inert pre-start state, so the caller can fix
        the cause and start again cleanly.
        """
        with self._transitions.hold("start()"):
            if self._started:
                raise SpocError("Framework is already started")

            base_dir = Path(base_dir)
            try:
                self._boot_discovery(base_dir)
                self.loader.initialize(self._hooks(), self._components_for())
            except BaseException:
                self._rollback()
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
        with self._transitions.claim("astart()"):
            if self._started:
                raise SpocError("Framework is already started")

            base_dir = Path(base_dir)
            try:
                self._boot_discovery(base_dir)
                await self.loader.ainitialize(self._hooks(), self._components_for())
            except BaseException:
                await self._arollback()
                raise

            self._started = True
            return self

    def shutdown(self) -> Framework:
        """Tear down modules in reverse dependency order, then reset to pre-start state.

        Everything the kernel owns is reset — registry, module bookkeeping,
        configuration. What persists is Python's own module cache and any
        module-level state: module-level code runs at most once per process,
        and a subsequent ``start`` re-runs discovery against those cached
        modules rather than re-executing them. No-op if never started.
        """
        with self._transitions.hold("shutdown()"):
            if not self._started:
                return self
            try:
                self.loader.shutdown(self._hooks(), self._components_for())
            finally:
                # Owed whether or not teardown succeeded: propagating the
                # failure and reaching the inert state are not alternatives.
                self._reset()
            return self

    async def ashutdown(self) -> Framework:
        """Asynchronous :meth:`shutdown`: awaits coroutine hooks and teardowns."""
        with self._transitions.claim("ashutdown()"):
            if not self._started:
                return self
            try:
                await self.loader.ashutdown(self._hooks(), self._components_for())
            finally:
                self._reset()
            return self

    def _rollback(self) -> None:
        """Tear down what came up, then reach the inert state whatever happened.

        A rollback runs while a boot failure is already unwinding, so its own
        failure must not replace the cause the caller has to act on. It is
        logged rather than raised — including a ``BaseException``, because the
        inert state is owed unconditionally and a stranded registry would
        outlive the failure that produced it.
        """
        try:
            self.loader.shutdown(self._hooks(), self._components_for())
        except BaseException:
            logger.error(_ROLLBACK_FAILED, exc_info=True)
        finally:
            self._reset()

    async def _arollback(self) -> None:
        """Asynchronous :meth:`_rollback`, with the same unconditional guarantee."""
        try:
            await self.loader.ashutdown(self._hooks(), self._components_for())
        except BaseException:
            logger.error(_ROLLBACK_FAILED, exc_info=True)
        finally:
            self._reset()

    def _reset(self) -> None:
        """Return every owned piece to its inert pre-start state.

        Clearing ``_started`` belongs here rather than at the call sites: they
        were two steps that both had to happen, which is precisely how one came
        to be skipped when a teardown raised. Reaching the inert state is now
        one operation that cannot be half-performed.
        """
        self.registry = Registry(self.kinds)
        self.loader = Loader()
        self.installed_apps = []
        self.config = None
        self.base_dir = None
        self._started = False

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
        # Namespaces are claimed from the full app list before anything is
        # imported, so a contested one fails with nothing registered rather
        # than partway through discovery — which is exactly the confusing
        # artifact this check exists to remove.
        entries = self._app_entries()
        owners: dict[str, str] = {}
        for entry in entries:
            _claim(owners, entry.namespace, entry.path)
        self._register_plugins(self.config.project, owners, entries)
        self._register_apps(entries)

        for loaded in self.loader.ordered():
            discover(self.registry, loaded.module, loaded.name, loaded.namespace)
        for callback in self._ready_callbacks:
            callback(self.registry)

    def _hooks(self) -> dict[str, KindHooks]:
        return {
            name: (spec.on_startup, spec.on_shutdown)
            for name, spec in self._specs.items()
        }

    def _components_for(self) -> Callable[[LoadedModule], tuple[Any, ...]]:
        """Build the lookup hook dispatch reads, grouped once for the phase.

        Dispatch asks per loaded module, and the registry answers each ask by
        scanning: M modules over N components is M scans, which made a phase
        quadratic in a project's own size. Grouping once turns the phase linear.

        The grouping is derived on read and lives only as long as the phase that
        reads it — it is never registry state, so there is nothing that could
        drift from the store. Deriving it from a single ``all()`` also means
        every hook in a phase reads *one* observation of the registry, the same
        guarantee :meth:`Registry.resolve` gives its failures.

        Built on first use rather than eagerly: only a kind that declares a hook
        ever asks, so a project with no hooks still pays nothing. The *registry*
        is bound now even though the grouping is not, so the phase reads the
        store it began with — ``_reset`` swaps the attribute rather than emptying
        the object, and binding at first call instead would make which registry a
        phase read depend on when its first hook happened to fire.
        """
        registry = self.registry
        grouped: dict[tuple[str, str], tuple[Any, ...]] | None = None

        def components_for(entry: LoadedModule) -> tuple[Any, ...]:
            nonlocal grouped
            if grouped is None:
                # all() enumerates in canonical-identifier order and grouping
                # preserves it, so each hook receives that same deterministic,
                # immutable view.
                collected: dict[tuple[str, str], list[Any]] = {}
                for c in registry.all():
                    collected.setdefault((c.kind, c.namespace), []).append(c.object)
                grouped = {key: tuple(objs) for key, objs in collected.items()}
            return grouped.get((entry.kind, entry.namespace), ())

        return components_for

    def _register_plugins(
        self,
        project: dict[str, Any],
        owners: dict[str, str],
        entries: list[_AppEntry],
    ) -> None:
        """Register config-declared references into the one flat registry.

        A ``[spoc.plugins]`` group names a declared kind — configuration is a
        second way to populate the registry, never a second registry. Identity
        follows the same grammar as discovery: a reference reads
        ``<app_path>.<module>.<attribute>``, so the segment before the module
        (the app path's final segment) is the namespace — a top-level module
        is its own namespace — and the attribute derives the object_name. A
        kind only plugins populate is declared ``required=False`` so apps
        need not provide a module for it.

        A reference inside an installed app takes *that app's* namespace, which
        is the app's stated one when it stated one — the package owns the name,
        not the path segment. A reference outside every installed app derives
        its own namespace and claims it; claiming one another package already
        owns is the same contest an app-versus-app collision is, and fails the
        same way. Registering into your own app's namespace stays legal, since
        that is what the group is for.

        A configured reference is a name in a file — there is nowhere for it to
        carry metadata — so a kind that states a metadata contract cannot be
        populated this way, and says so rather than reporting a contract
        violation the author has no way to satisfy.
        """
        namespace_of_app = {entry.path: entry.namespace for entry in entries}
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
                package = ".".join(segments[:-1]) if len(segments) > 1 else segments[-1]
                namespace = namespace_of_app.get(package)
                if namespace is None:
                    namespace = validate_segment(
                        "namespace", package.rpartition(".")[2]
                    )
                    _claim(owners, namespace, package)
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

    def _app_entries(self) -> list[_AppEntry]:
        """The installed apps for the active mode, parsed but not yet imported."""
        assert self.config is not None
        return [
            _parse_app_entry(app)
            for app in self._collect_apps(
                self.config.project.get("mode", DEFAULT_MODE),
                self.config.project.get("apps", {}),
                self.config.project.get("modes", DEFAULT_MODES),
            )
        ]

    def _kind_ranks(self) -> dict[str, int]:
        """Each declared kind's place in the load order, deepest dependency first.

        Rank comes from the declaration and nothing else, so it is the same for
        every app and cannot be moved by a module that happens not to exist. Kinds
        at equal depth keep their declaration order, which makes the rank total:
        two kinds never tie, so the app position below is the only remaining
        tiebreak.
        """
        graph = {name: set(spec.depends_on) for name, spec in self._specs.items()}
        depth: dict[str, int] = {}
        try:
            for name in graphlib.TopologicalSorter(graph).static_order():
                depth[name] = 1 + max((depth[d] for d in graph[name]), default=-1)
        except graphlib.CycleError as e:
            # A cycle among declared kinds, which the module graph only surfaces
            # when some app actually provides both modules of the cycle.
            raise CircularDependencyError([str(n) for n in e.args[1]]) from e
        # Declaration order as a lookup rather than a list scanned per comparison:
        # `index()` inside a sort key is quadratic in the number of kinds.
        declared = {name: position for position, name in enumerate(self._specs)}
        ordered = sorted(declared, key=lambda name: (depth[name], declared[name]))
        return {name: rank for rank, name in enumerate(ordered)}

    def _register_apps(self, entries: list[_AppEntry]) -> None:
        ranks = self._kind_ranks()
        for app_index, entry in enumerate(entries):
            # The path is imported exactly as written; the namespace was either
            # derived from its final segment or stated by the entry, and has
            # already been validated and claimed.
            for spec in self._specs.values():
                self.loader.register(
                    f"{entry.path}.{spec.name}",
                    kind=spec.name,
                    app=entry.path,
                    namespace=entry.namespace,
                    dependencies=tuple(f"{entry.path}.{d}" for d in spec.depends_on),
                    required=spec.required,
                    # The effective list decides: mode cascade and duplicate
                    # suppression have already produced `entries`, so reordering
                    # `[spoc.apps]` is what reorders modules within a kind phase.
                    position=(ranks[spec.name], app_index),
                )
        self.installed_apps = [entry.path for entry in entries]
