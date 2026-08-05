"""
The component registry — the kernel's single flat store.

All registered components live in one enumerable collection of :class:`Component`
records, keyed by canonical identifier. Kind and namespace are queryable *facets* of that
one collection: every grouped view is derived on read, never maintained as independent
state that could drift.

The registry describes; it never executes. Resolution is a pure lookup that returns the
object uninvoked, and that fails per segment — kind, then namespace, then object_name —
so a typo is reported against the step that could not match it rather than as a blanket
"not found".

Nothing here imports the module loader or touches the filesystem. The registry is
constructed from a declaration and populated by discovery; it has no opinion about where
components came from.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from .exceptions import (
    DuplicateComponentError,
    UnknownKindError,
    UnknownNamespaceError,
    UnknownObjectError,
)
from .identity import compose, parse, validate_segment


@dataclass(frozen=True)
class Component:
    """One registry record — the unit of enumeration and projection."""

    identifier: str
    kind: str
    namespace: str
    name: str
    object: Any
    metadata: Any = field(default=None)


class Registry:
    """Flat store of component records with faceted, deterministic reads."""

    def __init__(self, kinds: tuple[str, ...] = ()) -> None:
        self._kinds: tuple[str, ...] = tuple(validate_segment("kind", k) for k in kinds)
        self._store: dict[str, Component] = {}
        # id() is stable here because _store holds a strong reference to every object.
        self._identifier_of: dict[int, str] = {}

    @property
    def kinds(self) -> tuple[str, ...]:
        """The declared kind set (closed; fixed at construction)."""
        return self._kinds

    def add(
        self,
        kind: str,
        namespace: str,
        name: str,
        obj: Any,
        metadata: Any = None,
    ) -> Component:
        """Register an object, building its record and canonical identifier.

        One object holds exactly one canonical identifier: re-registering an
        already-registered object (an instance imported into another app, say)
        returns its existing record rather than forking its identity. First
        registration wins — the later call's namespace and name are validated,
        then discarded along with the identifier they would have composed.
        """
        if kind not in self._kinds:
            raise UnknownKindError(kind, self._kinds)
        # Composed before the identity short-circuit: reusing an object is not a
        # licence to skip the segment grammar every other registration answers to.
        identifier = compose(kind, namespace, name)
        prior = self._identifier_of.get(id(obj))
        if prior is not None:
            return self._store[prior]
        if identifier in self._store:
            raise DuplicateComponentError(identifier, self._store[identifier].object)
        record = Component(
            identifier=identifier,
            kind=kind,
            namespace=namespace,
            name=name,
            object=obj,
            metadata=metadata,
        )
        self._store[identifier] = record
        self._identifier_of[id(obj)] = identifier
        return record

    # ── Reads: one store, derived views, deterministic order ──────────────

    def all(self) -> list[Component]:
        """Every record, ordered by identifier."""
        return sorted(self._store.values(), key=lambda c: c.identifier)

    def by_kind(self, kind: str) -> list[Component]:
        """Records of one kind, ordered by identifier."""
        return sorted(
            (c for c in self._store.values() if c.kind == kind),
            key=lambda c: c.identifier,
        )

    def by_namespace(self, namespace: str) -> list[Component]:
        """Records of one namespace, ordered by identifier."""
        return sorted(
            (c for c in self._store.values() if c.namespace == namespace),
            key=lambda c: c.identifier,
        )

    def namespaces(self, kind: str | None = None) -> tuple[str, ...]:
        """Namespaces present in the registry, optionally for one kind."""
        found = {
            c.namespace for c in self._store.values() if kind is None or c.kind == kind
        }
        return tuple(sorted(found))

    def __iter__(self) -> Iterator[Component]:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._store

    # ── Resolution: pure lookup, per-segment precise failure ──────────────

    def resolve(self, identifier: str) -> Component:
        """Resolve a canonical identifier to its record, failing per segment.

        Success is a single dict hit after the grammar check; the per-segment
        scans run only on the failure path, where precision is worth the walk.
        """
        parsed = parse(identifier)

        record = self._store.get(str(parsed))
        if record is not None:
            return record

        if parsed.kind not in self._kinds:
            raise UnknownKindError(parsed.kind, self._kinds)

        namespaces = self.namespaces(kind=parsed.kind)
        if parsed.namespace not in namespaces:
            raise UnknownNamespaceError(parsed.namespace, parsed.kind, namespaces)

        candidates = tuple(
            c.name for c in self.by_kind(parsed.kind) if c.namespace == parsed.namespace
        )
        raise UnknownObjectError(parsed.name, parsed.kind, parsed.namespace, candidates)
