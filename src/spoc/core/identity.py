"""
Canonical component identity: the grammar, and the one conversion that feeds it.

Every registered object is identified by exactly one canonical identifier:

    kind:namespace.object_name

Each segment is lowercase snake_case (``^[a-z][a-z0-9_]*$``). This module is the only
place the grammar is defined or validated — everything else calls :func:`parse` and
:func:`compose`.

Validation and conversion are deliberately separate, and the split is by *origin*, not by
value. A name the author **states** is used verbatim and validated; a name the kernel
**derives** from an object is converted to snake_case by :func:`to_snake_case` first, then
validated like any other value. So a PEP 8 class name yields the conventional segment
without the author restating it, while a stated name is never silently rewritten.

A segment is always a legal Python identifier by construction — the grammar admits
only lowercase snake_case — with one exception the language reserves:
:func:`escape_keyword` spells the handful of segments a keyword already owns. Both
places that must spell a segment as a Python name, the scaffold's generated
decorators and the navigation surface, take it from here so they cannot disagree.
"""

from __future__ import annotations

import keyword
import re
from functools import lru_cache
from typing import Final, NamedTuple

from .exceptions import InvalidSegmentError, MalformedIdentifierError

#: The one grammar rule every segment must satisfy.
SEGMENT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")

#: Human-readable form of the full grammar, used in error messages.
GRAMMAR: Final[str] = "kind:namespace.object_name (each segment ^[a-z][a-z0-9_]*$)"

_SEGMENT_NAMES: Final[tuple[str, str, str]] = ("kind", "namespace", "object_name")

#: Word boundaries inside a camel/Pascal name. Two rules, both needed: a lower/digit→upper
#: transition (``userAccount`` → ``user|Account``), and the tail of an acronym before a
#: capitalized word (``HTTPServer`` → ``HTTP|Server``). Without the second, acronyms
#: collapse into ``httpserver``.
_CAMEL_BOUNDARY: Final[re.Pattern[str]] = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_SEPARATORS: Final[re.Pattern[str]] = re.compile(r"[_\-]+")

#: Bounded so converting attacker- or user-supplied strings cannot grow the cache without
#: limit. Declaration-time names are far below this.
_CACHE_SIZE: Final[int] = 2048


class Identifier(NamedTuple):
    """A parsed canonical identifier.

    The segments carry the grammar's own names — ``object_name``, not ``name`` —
    so there is no second vocabulary to translate between here, the registry
    records, and the error messages.
    """

    kind: str
    namespace: str
    object_name: str

    def __str__(self) -> str:
        return f"{self.kind}:{self.namespace}.{self.object_name}"


@lru_cache(maxsize=_CACHE_SIZE)
def to_snake_case(value: str) -> str:
    """Convert any case style to snake_case. Used for derived names only."""
    spaced = _CAMEL_BOUNDARY.sub("_", value)
    words = [w for w in _SEPARATORS.sub("_", spaced).lower().split("_") if w]
    return "_".join(words)


def validate_segment(
    segment_name: str, value: str, *, derived_from: str | None = None
) -> str:
    """Return `value` unchanged if it conforms to the segment grammar, else raise.

    `derived_from` names the intrinsic name `value` was converted from, when the
    caller derived it rather than being handed it. The failure describes the path
    actually taken, so remediation advice never tells the author of a derived-name
    failure that their stated name was used verbatim.
    """
    if not isinstance(value, str) or not SEGMENT_PATTERN.match(value):
        raise InvalidSegmentError(segment_name, value, derived_from=derived_from)
    return value


def escape_keyword(name: str) -> str:
    """The name a Python keyword already owns, spelled legally — `class` → `class_`.

    A single trailing underscore is the language's own convention for this
    collision (PEP 8), which is why it is preferred to any rewording: a reader
    who has met `class_` in the standard library needs no explanation.
    `keyword.iskeyword` is the authoritative list and travels with the language,
    so no local table can fall behind it.

    The identifier itself is never escaped — only the Python name spelling it.
    ``models:shop.class`` keeps that identifier while being reached as
    ``objects.models.shop.class_``.
    """
    return f"{name}_" if keyword.iskeyword(name) else name


def compose(kind: str, namespace: str, object_name: str) -> str:
    """Compose a canonical identifier from three segments, validating each."""
    validate_segment("kind", kind)
    validate_segment("namespace", namespace)
    validate_segment("object_name", object_name)
    return f"{kind}:{namespace}.{object_name}"


def parse(identifier: str) -> Identifier:
    """Parse a canonical identifier into its three segments.

    The type check stays *outside* the cache. ``lru_cache`` hashes its argument
    before the body runs, so an unhashable identifier would raise ``TypeError``
    from the cache machinery instead of this module's own grammar error — the
    caller would learn that a list is unhashable rather than that it is not an
    identifier.
    """
    if not isinstance(identifier, str):
        raise MalformedIdentifierError(repr(identifier), "identifier must be a string")
    return _parse(identifier)


@lru_cache(maxsize=_CACHE_SIZE)
def _parse(identifier: str) -> Identifier:
    """Parse a string identifier, memoized on the exact string.

    Parsing is pure and :class:`Identifier` is immutable, so a repeat parse can
    only produce a value equal to the first — resolution is the kernel's hottest
    path and it was spending four fifths of its time re-deriving that value from
    a string that had already passed the grammar once.

    Bounded exactly as :func:`to_snake_case` is, and for the same reason: an
    application may resolve identifiers built from user input, and a cache
    without a ceiling would be the place that grows. Past the ceiling this
    degrades to the cost of not having cached, never to unbounded memory.

    Failures are not memoized — ``lru_cache`` does not store exceptions — so a
    malformed identifier is re-derived and re-reported every time, with the
    message it always had, and cannot occupy an entry.
    """
    kind, sep, rest = identifier.partition(":")
    if not sep:
        raise MalformedIdentifierError(
            identifier, "missing ':' between kind and namespace"
        )

    parts = rest.split(".")
    if len(parts) < 2:
        raise MalformedIdentifierError(
            identifier, "missing '.' between namespace and object_name"
        )
    if len(parts) > 2:
        raise MalformedIdentifierError(
            identifier,
            f"expected exactly 3 segments, got {len(parts) + 1} "
            "(an operation suffix is not part of the grammar)",
        )

    namespace, object_name = parts
    for segment_name, value in zip(
        _SEGMENT_NAMES, (kind, namespace, object_name), strict=True
    ):
        validate_segment(segment_name, value)

    return Identifier(kind=kind, namespace=namespace, object_name=object_name)
