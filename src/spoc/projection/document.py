"""
The projection document: the registry as data, and its serialization.

Pure in, pure out. Nothing here boots a project, reads a file, or imports app
code — it turns records that already exist into a document, and that document
into text. The producer lives next door in :mod:`spoc.projection.produce`; the
split is the same one the stub generator draws between describing and emitting,
and for the same reason: a change to discovery cannot silently reshape the
document, and a change to the document cannot reach back into discovery.

**The document is the format; these dataclasses are one producer of it.** Field
names here follow the document, never the reverse. That is what makes this a
format another language can implement rather than an API it must mirror, and it
is why the published schema is written by hand rather than derived from these
classes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from ..core.registry import Component
from ..core.shape import Shape, shape_of

__all__ = [
    "FORMAT_VERSION",
    "ComponentEntry",
    "Projection",
    "dumps",
]

#: The version of the *format*, not of the framework. A document found on disk
#: years after the tool that wrote it still says what it is, and a consumer
#: branches on this rather than on a release number it would have to look up.
#: It changes when the document shape changes, and at no other time.
FORMAT_VERSION = "1.0"


def _location_of(obj: object) -> str:
    """Where a registered object is defined, as ``module:qualname``.

    A class or a function carries its own definition site. A registered
    *instance* does not — it was constructed somewhere, not defined — so the
    location names the site of its **type** instead. That is the nearest true
    answer, and the only stable one: an object's ``repr`` normally embeds its
    memory address, which would make two projections of one unchanged registry
    differ and defeat the entire point of a diffable document.
    """
    module = getattr(obj, "__module__", None)
    qualname = getattr(obj, "__qualname__", None)
    if module and qualname:
        return f"{module}:{qualname}"
    declaring = type(obj)
    return f"{declaring.__module__}:{declaring.__qualname__}"


@dataclass(frozen=True)
class ComponentEntry:
    """One registered component, described for a consumer outside the process.

    The three grammar facets travel alongside the identifier they compose, so a
    consumer never has to parse ``kind:namespace.object_name`` to filter on it —
    the format states what the grammar already knows.
    """

    identifier: str
    kind: str
    namespace: str
    object_name: str
    location: str
    shape: Shape

    @classmethod
    def from_component(cls, component: Component[Any]) -> ComponentEntry:
        return cls(
            identifier=component.identifier,
            kind=component.kind,
            namespace=component.namespace,
            object_name=component.object_name,
            location=_location_of(component.object),
            shape=shape_of(component.object),
        )


@dataclass(frozen=True)
class Projection:
    """A booted registry, described as data.

    ``kinds`` is the project's *declared* set, which is why a kind with no
    components still appears: "declared and empty" and "never declared" are
    different facts, and a consumer that cannot tell them apart cannot report
    on either.
    """

    kinds: tuple[str, ...]
    components: tuple[ComponentEntry, ...]
    format_version: str = FORMAT_VERSION

    def to_dict(self) -> dict[str, Any]:
        """The document, as the plain structures ``json`` serializes.

        Key order is fixed here rather than sorted on the way out: the version
        leads because it is what a consumer reads first to decide whether it
        understands the rest.
        """
        return {
            "format_version": self.format_version,
            "kinds": list(self.kinds),
            "components": [asdict(entry) for entry in self.components],
        }


def dumps(projection: Projection) -> str:
    """Render `projection` as the canonical document text.

    Deterministic by construction: entries arrive in canonical identifier
    order, key order is the dataclasses' own, and no value here depends on the
    clock, the filesystem, or the order apps were declared in.

    Escapes non-ASCII rather than emitting it. The document is written to
    standard output and piped onward, and a console whose encoding is not UTF-8
    would otherwise turn a describable project into an encoding error — the one
    failure mode a *description* must not have.
    """
    return json.dumps(projection.to_dict(), indent=2, ensure_ascii=True) + "\n"
