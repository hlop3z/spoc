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

import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Final

from .exceptions import (
    DuplicateComponentError,
    IdentityDivergenceError,
    UnknownKindError,
    UnknownNamespaceError,
    UnknownObjectError,
)
from .identity import compose, parse, validate_segment

#: Types whose instances the runtime is free to share — small integers and many
#: strings are interned, ``()`` is a singleton. For these, ``id()`` is not a
#: proxy for "the same declared object": two registrations that merely hold
#: equal values would collide in the divergence map and be reported as one
#: object claiming two identities. They are excluded from that map instead.
_SHARED_VALUE_TYPES: Final[tuple[type, ...]] = (
    int,  # bool is a subclass
    float,
    complex,
    str,
    bytes,
    tuple,
    frozenset,
    type(None),
)


@dataclass(frozen=True)
class Component[T]:
    """One registry record — the unit of enumeration and projection.

    The three segment fields carry the grammar's own names, so a projection
    reads ``kind``/``namespace``/``object_name`` here, in a parsed identifier,
    and in an error message alike.

    The type parameter describes the registered object. Registration cannot know
    it — :meth:`Registry.add` takes an object of any type and hands back
    ``Component[Any]`` — so it exists for *readers* that do know: a generated
    stub narrows ``resolve`` per identifier, and a typed accessor narrows it per
    call. Written bare, ``Component`` places no constraint on ``object``, which
    is what every unnarrowed reader means.
    """

    identifier: str
    kind: str
    namespace: str
    object_name: str
    object: T
    metadata: Any = field(default=None)


class Registry:
    """Flat store of component records with faceted, deterministic reads.

    Concurrency contract: registrations are serialized — each ``add`` is
    atomic, none is lost, and the duplicate and divergence guarantees hold
    under any interleaving. Reads snapshot the store under the same lock, so
    a read concurrent with writers observes only complete records. After
    boot, when nothing writes, reads contend on nothing but an uncontested
    lock acquisition.
    """

    def __init__(self, kinds: tuple[str, ...] = ()) -> None:
        self._kinds: tuple[str, ...] = tuple(validate_segment("kind", k) for k in kinds)
        self._store: dict[str, Component[Any]] = {}
        # id() is stable here because _store holds a strong reference to every object.
        self._identifier_of: dict[int, str] = {}
        self._lock = threading.Lock()

    @property
    def kinds(self) -> tuple[str, ...]:
        """The declared kind set (closed; fixed at construction)."""
        return self._kinds

    def add(
        self,
        kind: str,
        namespace: str,
        object_name: str,
        obj: Any,
        metadata: Any = None,
    ) -> Component[Any]:
        """Register an object, building its record and canonical identifier.

        One object holds exactly one canonical identifier. Re-registering an
        object under its existing identity is idempotent and returns the
        existing record; re-registering it under a *different* identity raises
        — the registry never answers a registration with a record whose
        identity differs from what the caller stated.

        Divergence is a claim about *objects*, so it is tracked only for those
        whose identity is their own (see :data:`_SHARED_VALUE_TYPES`).
        """
        if kind not in self._kinds:
            raise UnknownKindError(kind, self._kinds)
        identifier = compose(kind, namespace, object_name)
        tracked = not isinstance(obj, _SHARED_VALUE_TYPES)
        with self._lock:
            if tracked:
                prior = self._identifier_of.get(id(obj))
                if prior is not None:
                    if prior != identifier:
                        raise IdentityDivergenceError(prior, identifier)
                    return self._store[prior]
            existing = self._store.get(identifier)
            if existing is not None:
                # The same object under the same identifier is idempotent even
                # when it is a shared value the divergence map does not track.
                if existing.object is obj:
                    return existing
                raise DuplicateComponentError(identifier, existing.object)
            record = Component(
                identifier=identifier,
                kind=kind,
                namespace=namespace,
                object_name=object_name,
                object=obj,
                metadata=metadata,
            )
            self._store[identifier] = record
            if tracked:
                self._identifier_of[id(obj)] = identifier
            return record

    def identifier_of(self, obj: Any) -> str | None:
        """The canonical identifier `obj` is registered under, or None.

        Always None for a shared value type, whose ``id()`` says nothing about
        which registration it came from.
        """
        if isinstance(obj, _SHARED_VALUE_TYPES):
            return None
        with self._lock:
            return self._identifier_of.get(id(obj))

    # ── Reads: one store, derived views, deterministic order ──────────────

    def _snapshot(self) -> list[Component[Any]]:
        with self._lock:
            return list(self._store.values())

    def all(self) -> list[Component[Any]]:
        """Every record, ordered by identifier."""
        return sorted(self._snapshot(), key=lambda c: c.identifier)

    def by_kind(self, kind: str) -> list[Component[Any]]:
        """Records of one kind, ordered by identifier."""
        return sorted(
            (c for c in self._snapshot() if c.kind == kind),
            key=lambda c: c.identifier,
        )

    def by_namespace(self, namespace: str) -> list[Component[Any]]:
        """Records of one namespace, ordered by identifier."""
        return sorted(
            (c for c in self._snapshot() if c.namespace == namespace),
            key=lambda c: c.identifier,
        )

    def namespaces(self, kind: str | None = None) -> tuple[str, ...]:
        """Namespaces present in the registry, optionally for one kind."""
        found = {
            c.namespace for c in self._snapshot() if kind is None or c.kind == kind
        }
        return tuple(sorted(found))

    def __iter__(self) -> Iterator[Component[Any]]:
        return iter(self.all())

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, identifier: str) -> bool:
        with self._lock:
            return identifier in self._store

    # ── Resolution: pure lookup, per-segment precise failure ──────────────

    def resolve(self, identifier: str) -> Component[Any]:
        """Resolve a canonical identifier to its record, failing per segment.

        Success is a single dict hit after the grammar check; the per-segment
        scans run only on the failure path, where precision is worth the walk.
        """
        parsed = parse(identifier)

        with self._lock:
            record = self._store.get(str(parsed))
        if record is not None:
            return record

        if parsed.kind not in self._kinds:
            raise UnknownKindError(parsed.kind, self._kinds)

        namespaces = self.namespaces(kind=parsed.kind)
        if parsed.namespace not in namespaces:
            raise UnknownNamespaceError(parsed.namespace, parsed.kind, namespaces)

        candidates = tuple(
            c.object_name
            for c in self.by_kind(parsed.kind)
            if c.namespace == parsed.namespace
        )
        raise UnknownObjectError(
            parsed.object_name, parsed.kind, parsed.namespace, candidates
        )
