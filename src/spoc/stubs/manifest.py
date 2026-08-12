"""
The manifest: what a booted project's resolution surface looks like, frozen.

Describing a project is a *collect-only* boot. The kernel already separates
"work out what exists" from "start it": :meth:`Framework.start` runs discovery
and then initializes modules, so describing reuses the first half and stops.
No initializer runs, no lifecycle hook fires, and the framework is reset
afterwards — including when describing fails — so a description leaves nothing
behind that an ordinary start would not have.

The manifest is the boundary between describing and emitting. The emitter never
introspects anything; it consumes this. That is what keeps a change to discovery
from silently skewing the stub, and a new emitter from being able to break
discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from ..core.exceptions import SpocError
from ..framework import Framework
from .extract import Shape, TypeRef, reference_for, shape_of


class UnmirrorableRootError(SpocError):
    """The composition root holds names the stub cannot describe.

    A stub shadows its module wholesale for type checking, so anything the
    emitter cannot mirror would silently vanish from the checker's view. The
    convention this relies on — a composition root holds the framework and its
    kind handles, nothing else — is the one Rule 2 already asks for; here it
    becomes load-bearing, so it is enforced rather than assumed.
    """

    def __init__(self, module_name: str, names: tuple[str, ...]) -> None:
        self.module_name, self.names = module_name, names
        listed = ", ".join(names)
        super().__init__(
            f"Composition root {module_name!r} exports {listed} — names the stub "
            "cannot describe. Move them to another module: a generated stub "
            "replaces this module for type checking, so anything it cannot "
            "mirror would disappear from the type checker's view"
        )


@dataclass(frozen=True)
class Entry:
    """One resolvable identifier and the static type reading it yields."""

    identifier: str
    kind: str
    namespace: str
    object_name: str
    shape: Shape
    type_ref: TypeRef


@dataclass(frozen=True)
class Handle:
    """A kind registration handle exported by the composition root."""

    attribute: str
    kind: str


@dataclass(frozen=True)
class Manifest:
    """Everything an emitter needs, and nothing that requires introspection."""

    root_module: str
    framework_attribute: str
    kinds: tuple[str, ...]
    handles: tuple[Handle, ...]
    entries: tuple[Entry, ...]

    @property
    def degraded(self) -> int:
        """How many entries could not be described faithfully."""
        return sum(1 for entry in self.entries if entry.type_ref.degraded)


def _entries(framework: Framework) -> tuple[Entry, ...]:
    """One entry per registered component, in canonical identifier order.

    ``Registry.all`` already sorts by identifier, so emission order is a
    property of the grammar rather than of declaration or load order.
    """
    return tuple(
        Entry(
            identifier=record.identifier,
            kind=record.kind,
            namespace=record.namespace,
            object_name=record.object_name,
            shape=shape_of(record.object),
            type_ref=reference_for(record.object),
        )
        for record in framework.registry.all()
    )


def _surface(root: ModuleType, framework: Framework) -> tuple[str, tuple[Handle, ...]]:
    """The composition root's mirrorable surface: the binding and the handles.

    Anything else public and locally defined is refused rather than dropped.
    """
    root_name = getattr(root, "__name__", "<unknown>")
    binding: str | None = None
    handles: list[Handle] = []
    unmirrorable: list[str] = []

    for attribute in sorted(vars(root)):
        if attribute.startswith("_"):
            continue
        value = getattr(root, attribute)
        if isinstance(value, ModuleType):
            continue  # an import, not part of this module's surface
        kind = getattr(value, "__spoc_kind__", None)
        if isinstance(kind, str):
            handles.append(Handle(attribute=attribute, kind=kind))
            continue
        if value is framework:
            binding = attribute
            continue
        if getattr(value, "__module__", root_name) != root_name:
            continue  # imported name, declared elsewhere
        unmirrorable.append(attribute)

    if unmirrorable:
        raise UnmirrorableRootError(root_name, tuple(unmirrorable))
    if binding is None:
        raise UnmirrorableRootError(root_name, ("<no Framework instance bound>",))
    return binding, tuple(handles)


def describe(framework: Framework, base_dir: Path | str, root: ModuleType) -> Manifest:
    """Collect-only boot of `framework`, returned as a manifest.

    Discovery runs; initialization does not. The framework is returned to its
    pre-description state before this returns, on both the success and the
    failure path, so describing a project is never a way to half-start it.
    """
    if framework.started:
        raise SpocError(
            "Cannot describe a started framework: describing runs its own "
            "collect-only boot and would race the running one"
        )

    # The collect-only half of start(): discovery, without initialization.
    boot: Any = framework._boot_discovery
    try:
        boot(Path(base_dir))
        entries = _entries(framework)
        binding, handles = _surface(root, framework)
        return Manifest(
            root_module=getattr(root, "__name__", "<unknown>"),
            framework_attribute=binding,
            kinds=framework.kinds,
            handles=handles,
            entries=entries,
        )
    finally:
        # Leave nothing behind that an ordinary start would not have.
        framework._reset()
