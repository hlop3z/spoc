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
"""

from __future__ import annotations

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


def compose(kind: str, namespace: str, object_name: str) -> str:
    """Compose a canonical identifier from three segments, validating each."""
    validate_segment("kind", kind)
    validate_segment("namespace", namespace)
    validate_segment("object_name", object_name)
    return f"{kind}:{namespace}.{object_name}"


def parse(identifier: str) -> Identifier:
    """Parse a canonical identifier into its three segments."""
    if not isinstance(identifier, str):
        raise MalformedIdentifierError(repr(identifier), "identifier must be a string")

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
