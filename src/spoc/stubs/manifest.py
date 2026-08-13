"""
The manifest: what a booted project's resolution surface looks like, frozen.

Describing a project is a *collect-only* boot, and this module does not own one:
it borrows :func:`spoc.projection.collected`, so the stub and the registry
projection describe a registry at the same depth by construction rather than by
two modules agreeing to.

What the manifest adds to a projection is exactly what a *type checker* needs
and a language-neutral document must not carry: the static type each identifier
yields, and the composition root's mirrorable surface. Everything a consumer in
another language could act on — the identifier, its facets, the location, the
shape — is the projection's, read from it rather than recomputed here.

The manifest is the boundary between describing and emitting. The emitter never
introspects anything; it consumes this. That is what keeps a change to discovery
from silently skewing the stub, and a new emitter from being able to break
discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from ..core.exceptions import SpocError
from ..core.shape import Shape
from ..framework import Framework
from ..projection import ComponentEntry, Projection
from ..projection.produce import collected, projection_of
from .extract import TypeRef, reference_for


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
    """One resolvable identifier and the static type reading it yields.

    A projection entry plus the one Python-specific fact the projection refuses
    to carry. The facets are read through, not copied into new fields, so there
    is no second place where an identifier's kind could be recorded wrongly.
    """

    component: ComponentEntry
    type_ref: TypeRef

    @property
    def identifier(self) -> str:
        return self.component.identifier

    @property
    def kind(self) -> str:
        return self.component.kind

    @property
    def namespace(self) -> str:
        return self.component.namespace

    @property
    def object_name(self) -> str:
        return self.component.object_name

    @property
    def shape(self) -> Shape:
        return self.component.shape


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
    projection: Projection
    handles: tuple[Handle, ...]
    entries: tuple[Entry, ...]

    @property
    def kinds(self) -> tuple[str, ...]:
        """The declared kind set, read from the projection that states it."""
        return self.projection.kinds

    @property
    def degraded(self) -> int:
        """How many entries could not be described faithfully."""
        return sum(1 for entry in self.entries if entry.type_ref.degraded)

    @property
    def navigation(self) -> dict[str, dict[str, tuple[Entry, ...]]]:
        """The same entries, grouped as the navigation surface walks them.

        A view over :attr:`entries`, not a second collection: the emitter needs
        kind → namespace → entries to render nested members, and grouping here
        keeps that regrouping out of the emitter while leaving one source for
        what the project registered. Insertion order is canonical identifier
        order, because that is the order `entries` already carries.
        """
        grouped: dict[str, dict[str, list[Entry]]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.kind, {}).setdefault(entry.namespace, []).append(
                entry
            )
        return {
            kind: {
                namespace: tuple(entries) for namespace, entries in namespaces.items()
            }
            for kind, namespaces in grouped.items()
        }


def _entries(projection: Projection, framework: Framework) -> tuple[Entry, ...]:
    """One entry per projected component, in the projection's own order.

    Order is not re-established here. The projection already emits in canonical
    identifier order, and re-sorting would be a second claim to the same
    guarantee — one that could later disagree with the first.
    """
    return tuple(
        Entry(
            component=component,
            type_ref=reference_for(
                framework.registry.resolve(component.identifier).object
            ),
        )
        for component in projection.components
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
    with collected(framework, base_dir) as discovered:
        projection = projection_of(discovered)
        binding, handles = _surface(root, discovered)
        return Manifest(
            root_module=getattr(root, "__name__", "<unknown>"),
            framework_attribute=binding,
            projection=projection,
            handles=handles,
            entries=_entries(projection, discovered),
        )
