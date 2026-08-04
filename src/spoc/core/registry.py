"""
The component registry — the kernel's single flat store.

All registered components live in one enumerable collection of
:class:`Component` records, keyed by canonical identifier. Kind and namespace
are queryable facets of that one collection; every grouped view is derived,
never maintained as independent state.

The registry describes — it never executes. Resolution is a pure lookup that
fails per segment with a precise error; it never calls, constructs, or
otherwise invokes what it returns.
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
from .identifier import compose, parse, validate_segment


@dataclass(frozen=True)
class Component:
    """
    One registry record — the unit of enumeration and projection.

    A record carries everything an external surface needs to build a
    projection (routes, schemas, docs) by reading it alone: the canonical
    identifier, its three segments individually, the registered object, and
    the configuration and metadata supplied at registration.
    """

    identifier: str
    kind: str
    namespace: str
    name: str
    object: Any
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class Registry:
    """
    Single flat store of component records with faceted, deterministic reads.

    The kind set is closed at construction time — registering under an
    unknown kind raises; there is no API to extend the set at runtime.
    """

    def __init__(self, kinds: tuple[str, ...] = ()) -> None:
        """
        Args:
            kinds: The declared (closed) kind set, fixed at composition time.
                Each kind must conform to the segment grammar.
        """
        self._kinds: tuple[str, ...] = tuple(validate_segment("kind", k) for k in kinds)
        self._store: dict[str, Component] = {}

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
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Component:
        """
        Register an object, building its record and canonical identifier.

        Raises:
            UnknownKindError: If ``kind`` is not in the declared set.
            InvalidSegmentError: If any segment violates the grammar.
            DuplicateComponentError: If the identifier is already registered.
        """
        if kind not in self._kinds:
            raise UnknownKindError(kind, self._kinds)
        identifier = compose(kind, namespace, name)
        if identifier in self._store:
            existing = self._store[identifier]
            if existing.object is obj:
                return existing  # same object re-discovered — not a duplicate
            raise DuplicateComponentError(identifier, existing.object)
        record = Component(
            identifier=identifier,
            kind=kind,
            namespace=namespace,
            name=name,
            object=obj,
            config=dict(config or {}),
            metadata=dict(metadata or {}),
        )
        self._store[identifier] = record
        return record

    # ── Reads: one store, derived views, deterministic order ──────────────

    def all(self) -> list[Component]:
        """Every record, ordered by identifier."""
        return sorted(self._store.values(), key=lambda c: c.identifier)

    def by_kind(self, kind: str) -> list[Component]:
        """Records of one kind, ordered by identifier."""
        return [c for c in self.all() if c.kind == kind]

    def by_namespace(self, namespace: str) -> list[Component]:
        """Records of one namespace, ordered by identifier."""
        return [c for c in self.all() if c.namespace == namespace]

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
        """
        Resolve a canonical identifier to its record.

        Checks proceed in the fixed order kind → namespace → object_name;
        each step raises a dedicated error naming the failing segment, its
        value, and the candidates valid at that step. The resolved object is
        returned unexecuted — invocation is the caller's responsibility.

        Raises:
            MalformedIdentifierError: If the string doesn't parse.
            InvalidSegmentError: If a segment violates the grammar.
            UnknownKindError: If the kind is not declared.
            UnknownNamespaceError: If no such namespace holds that kind.
            UnknownObjectError: If the name is absent in kind:namespace.
        """
        parsed = parse(identifier)

        if parsed.kind not in self._kinds:
            raise UnknownKindError(parsed.kind, self._kinds)

        namespaces = self.namespaces(kind=parsed.kind)
        if parsed.namespace not in namespaces:
            raise UnknownNamespaceError(parsed.namespace, parsed.kind, namespaces)

        record = self._store.get(str(parsed))
        if record is None:
            candidates = tuple(
                c.name
                for c in self.by_kind(parsed.kind)
                if c.namespace == parsed.namespace
            )
            raise UnknownObjectError(
                parsed.name, parsed.kind, parsed.namespace, candidates
            )
        return record
