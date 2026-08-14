"""
The component registry — the kernel's single flat store.

All registered components live in one enumerable collection of :class:`Component`
records, keyed by the grammar's own segments — kind, then namespace, then object name.
Kind and namespace are therefore *facets* in the literal sense: a facet is a
sub-dictionary of the one store, not a view maintained beside it. Nothing is kept in
step with anything, because there is only one thing.

That shape is what an identifier already means, so it costs no fidelity: ``parse``
transforms nothing and the grammar admits neither ``:`` nor ``.``, which makes reaching
a record through three segments and through its composed string the same lookup written
two ways. It is also what makes reading one facet cost that facet rather than everything
registered — the difference between microseconds and milliseconds at scale, and the
reason a grouped view never has to be derived by walking the whole collection.

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
    MalformedIdentifierError,
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

    The guarantee covers failure *messages*, not only records: a failed
    :meth:`resolve` describes one observation of the store rather than several
    stitched together. That is stated here because the obvious implementation —
    asking the faceted readers for candidates once the lookup has released the
    lock — quietly does not hold it.
    """

    def __init__(self, kinds: tuple[str, ...] = ()) -> None:
        self._kinds: tuple[str, ...] = tuple(validate_segment("kind", k) for k in kinds)
        # The store, keyed by the grammar's own segments: kind → namespace →
        # object name. One structure, not a flat store with facet indexes beside
        # it — a facet is a sub-dictionary of this, so no facet can disagree with
        # the whole, and nothing has to be kept in step with anything.
        #
        # Keying this way is what an identifier means. `parse` transforms nothing
        # and the grammar admits neither ':' nor '.', so reaching a record through
        # its three segments and reaching it through its composed string are the
        # same lookup written two ways.
        self._components: dict[str, dict[str, dict[str, Component[Any]]]] = {}
        self._count = 0
        # id() is stable here because the store holds a strong reference to every
        # object. Not a view of the store — the inverse question, which segment
        # triple an object was registered under — so it cannot be read off a facet
        # and is maintained instead. `_admit` is the only writer of either.
        self._identifier_of: dict[int, str] = {}
        self._lock = threading.Lock()

    def _admit(self, record: Component[Any], obj: Any, tracked: bool) -> None:
        """Admit a record to the registry. **The only mutator of registry state.**

        Every write goes through here, so a record cannot exist for one reader and
        not another, and the identity map cannot fall out of step with the store.
        The store being a single structure makes facet drift unrepresentable; this
        method is what extends that to the identity map beside it, and a test in
        the suite fails if a second writer ever appears.

        The caller holds the lock.
        """
        self._components.setdefault(record.kind, {}).setdefault(record.namespace, {})[
            record.object_name
        ] = record
        self._count += 1
        if tracked:
            self._identifier_of[id(obj)] = record.identifier

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
                if prior is not None and prior != identifier:
                    raise IdentityDivergenceError(prior, identifier)
                # A `prior` equal to `identifier` needs no separate answer: the
                # record is in the store under exactly those segments, and the
                # idempotent return below finds it.
            existing = self._at(kind, namespace, object_name)
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
            self._admit(record, obj, tracked)
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

    # ── Reads: sub-dictionaries of the one store, deterministic order ─────

    def _at(self, kind: str, namespace: str, object_name: str) -> Component[Any] | None:
        """The record under three segments, or None. The caller holds the lock."""
        return self._components.get(kind, {}).get(namespace, {}).get(object_name)

    def _snapshot(self) -> list[Component[Any]]:
        with self._lock:
            return [
                record
                for by_namespace in self._components.values()
                for by_name in by_namespace.values()
                for record in by_name.values()
            ]

    def all(self) -> list[Component[Any]]:
        """Every record, ordered by identifier."""
        return sorted(self._snapshot(), key=lambda c: c.identifier)

    def by_kind(self, kind: str) -> list[Component[Any]]:
        """Records of one kind, ordered by identifier."""
        with self._lock:
            found = [
                record
                for by_name in self._components.get(kind, {}).values()
                for record in by_name.values()
            ]
        return sorted(found, key=lambda c: c.identifier)

    def by_namespace(self, namespace: str) -> list[Component[Any]]:
        """Records of one namespace, ordered by identifier.

        Across kinds, so this walks the kind spine — a closed set fixed at
        construction — rather than every record.
        """
        with self._lock:
            found = [
                record
                for by_namespace in self._components.values()
                for record in by_namespace.get(namespace, {}).values()
            ]
        return sorted(found, key=lambda c: c.identifier)

    def namespaces(self, kind: str | None = None) -> tuple[str, ...]:
        """Namespaces present in the registry, optionally for one kind."""
        with self._lock:
            if kind is not None:
                found = set(self._components.get(kind, {}))
            else:
                found = {ns for by_ns in self._components.values() for ns in by_ns}
        return tuple(sorted(found))

    def object_names(self, kind: str, namespace: str) -> tuple[str, ...]:
        """Object names registered under one kind and namespace, sorted.

        The narrowest read. Internal to the type: the promised way to read this
        is :meth:`by_kind` or navigation. Ordering costs the facet, so a caller
        that only needs to know whether one name is there asks :meth:`holds`.
        """
        with self._lock:
            found = tuple(self._components.get(kind, {}).get(namespace, {}))
        return tuple(sorted(found))

    def holds(
        self,
        kind: str,
        namespace: str | None = None,
        object_name: str | None = None,
    ) -> bool:
        """Whether anything is registered under these segments.

        The membership question at whatever depth a caller has reached, so a
        navigation step that will succeed pays a dict hit rather than the ordered
        facet it would have thrown away. The ordered facet is what a *failure*
        needs — to name what it could have matched — and failure is where paying
        for it buys something. Same shape as resolution, for the same reason.
        """
        with self._lock:
            by_namespace = self._components.get(kind)
            if by_namespace is None:
                return False
            if namespace is None:
                return True
            by_name = by_namespace.get(namespace)
            if by_name is None:
                return False
            return object_name is None or object_name in by_name

    def __iter__(self) -> Iterator[Component[Any]]:
        return iter(self.all())

    def __len__(self) -> int:
        with self._lock:
            return self._count

    def __contains__(self, identifier: str) -> bool:
        # A membership test answers about *this* registry, so a string the
        # grammar refuses is simply not in it — the same answer a flat mapping
        # keyed by identifier gave, without the caller having to guard the call.
        try:
            parsed = parse(identifier)
        except MalformedIdentifierError:
            return False
        with self._lock:
            return (
                self._at(parsed.kind, parsed.namespace, parsed.object_name) is not None
            )

    # ── Resolution: pure lookup, per-segment precise failure ──────────────

    def resolve(self, identifier: str) -> Component[Any]:
        """Resolve a canonical identifier to its record, failing per segment.

        Success is a single dict hit after the grammar check; the per-segment
        scans run only on the failure path, where precision is worth the walk.

        A failure is composed from **one** observation of the store — the same
        one that failed to find the identifier — so it can never name a
        candidate that did not exist at lookup time, nor report a segment as
        unknown that the observation contains. The scans run over that snapshot
        in pure code rather than re-acquiring the lock per segment, which is
        also strictly fewer acquisitions than deriving them from the faceted
        readers.
        """
        # Parsed for the grammar check and for the segments the failure path
        # needs; the *key* is the caller's own string. Parsing transforms
        # nothing and the segment grammar admits neither ':' nor '.', so the
        # split is unambiguous and `str(parse(x))` is `x` — rebuilding it was
        # composing a string the caller had already handed over.
        parsed = parse(identifier)

        with self._lock:
            by_namespace = self._components.get(parsed.kind, {})
            by_name = by_namespace.get(parsed.namespace, {})
            record = by_name.get(parsed.object_name)
            if record is not None:
                return record
            # The one observation the failure is composed from, taken in the same
            # acquisition that failed to find the record — and only the two levels
            # a failure can name, rather than a copy of everything registered.
            namespaces = tuple(sorted(by_namespace))
            candidates = tuple(sorted(by_name))

        # The declared kind set is fixed at construction, so it needs no lock.
        if parsed.kind not in self._kinds:
            raise UnknownKindError(parsed.kind, self._kinds)
        if parsed.namespace not in namespaces:
            raise UnknownNamespaceError(parsed.namespace, parsed.kind, namespaces)
        raise UnknownObjectError(
            parsed.object_name, parsed.kind, parsed.namespace, candidates
        )
