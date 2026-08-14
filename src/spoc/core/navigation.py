"""
The registry, navigated: ``objects.models.shop.product`` instead of a string.

The identity grammar is ``kind:namespace.object_name``. Reaching a component by
that string is one lookup; reaching it by *walking those three facets as
attributes* is the same lookup and the same record, spelled so a type checker
can describe every step. That spelling is the whole reason this module exists —
the description a checker builds from it stays flat where a per-identifier
narrowing does not, at the registry sizes a framework built on SPOC reaches.

Nothing is materialized. Each step reads the registry it was handed at the
moment it is asked, so the navigation surface cannot drift from the store: it
*is* the store, walked by a different route. That also means a component
registered after a step was taken is visible to the next one.

Three levels, one rule each:

    objects            -> a kind        (the declared kind set)
    objects.models     -> a namespace   (namespaces holding that kind)
    objects.models.shop -> a component  (the record resolve() returns)

A segment a Python keyword owns is spelled with the language's own escape
(``class`` -> ``class_``, :func:`~spoc.core.identity.escape_keyword`). The
identifier never changes; only the attribute spelling does.

Failures reuse the registry's per-segment errors, so navigating to a name that
is not there says exactly what resolving the equivalent identifier would say —
the segment that failed and the candidates at it. A caller who mistypes gets one
answer, whichever route they took.
"""

from __future__ import annotations

from typing import Any

from .exceptions import UnknownKindError, UnknownNamespaceError, UnknownObjectError
from .identity import escape_keyword
from .registry import Component, Registry


class _Level:
    """One step of the walk, holding the registry and how far it has come.

    A single class rather than three: the levels differ only in which facet
    they match on and which error they raise, and the walk is short enough that
    naming the difference in data beats three near-identical classes.
    """

    __slots__ = ("_kind", "_namespace", "_registry")

    def __init__(
        self, registry: Registry, kind: str | None = None, namespace: str | None = None
    ) -> None:
        self._registry = registry
        self._kind = kind
        self._namespace = namespace

    # ── Walking ───────────────────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        # Dunder lookups arrive here for anything __slots__ does not define —
        # copy, pickle, and every `hasattr(obj, "__len__")` style probe in the
        # standard library. Answering them with a registry lookup would invent
        # protocol support this object does not have, and the grammar never
        # admits such a name anyway.
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return self._step(name)

    def _step(self, name: str) -> Any:
        if self._kind is None:
            return self._into_kind(name)
        if self._namespace is None:
            return self._into_namespace(name)
        return self._into_component(name)

    def _into_kind(self, name: str) -> _Level:
        kinds = self._registry.kinds
        matched = _match(name, kinds)
        if matched is None:
            raise UnknownKindError(name, kinds)
        return _Level(self._registry, matched)

    def _into_namespace(self, name: str) -> _Level:
        kind = str(self._kind)
        if self._registry.holds(kind, name):
            return _Level(self._registry, self._kind, name)
        namespaces = self._namespaces()
        matched = _match(name, namespaces)
        if matched is None:
            raise UnknownNamespaceError(name, kind, namespaces)
        return _Level(self._registry, self._kind, matched)

    def _into_component(self, name: str) -> Component[Any]:
        kind, namespace = str(self._kind), str(self._namespace)
        # The overwhelmingly common step is the one that succeeds under the name
        # as written, and answering it needs one membership question, not the
        # facet's names in order. The ordered read below is what a failure needs
        # — to name the candidates — and what an escaped spelling needs, since
        # matching those means comparing against each one.
        matched: str | None = name
        if not self._registry.holds(kind, namespace, name):
            candidates = self._object_names()
            matched = _match(name, candidates)
            if matched is None:
                raise UnknownObjectError(name, kind, namespace, candidates)
        # Composed rather than searched: the identifier is the canonical route,
        # and resolving it here is what makes navigation and resolution the same
        # lookup rather than two implementations that agree by testing.
        return self._registry.resolve(f"{kind}:{namespace}.{matched}")

    # ── Reflection: what an editor, `dir()`, and a human get ──────────────

    def __dir__(self) -> list[str]:
        if self._kind is None:
            names: tuple[str, ...] = self._registry.kinds
        elif self._namespace is None:
            names = self._namespaces()
        else:
            names = self._object_names()
        return sorted(escape_keyword(name) for name in names)

    def __repr__(self) -> str:
        walked = ".".join(
            escape_keyword(part)
            for part in (self._kind, self._namespace)
            if part is not None
        )
        offers = len(self.__dir__())
        at = f" at {walked}" if walked else ""
        return f"<objects{at}: {offers} name(s)>"

    # ── Reading the store, once per question ──────────────────────────────

    def _namespaces(self) -> tuple[str, ...]:
        return self._registry.namespaces(self._kind)

    def _object_names(self) -> tuple[str, ...]:
        return self._registry.object_names(str(self._kind), str(self._namespace))


def _match(attribute: str, names: tuple[str, ...]) -> str | None:
    """The grammar segment an attribute spells, or None.

    Escaping is applied to the *candidates* rather than un-escaping the
    attribute, because the inverse is ambiguous: a project may legitimately
    declare both ``class`` and ``class_``, and stripping a trailing underscore
    would make the second unreachable. Comparing forward keeps every declared
    segment reachable by exactly one spelling.
    """
    if attribute in names:
        return attribute
    return next((name for name in names if escape_keyword(name) == attribute), None)


def navigator(registry: Registry) -> Any:
    """The navigation surface for `registry`.

    Returns `Any` deliberately: the useful type of this object is the generated
    stub's description of one project's registry, and no annotation written here
    could be more accurate than that. Claiming a narrower static type would
    fight the stub rather than defer to it.
    """
    return _Level(registry)
