"""
Canonical component identifier grammar.

Every registered object is identified by exactly one canonical identifier:

    kind:namespace.object_name

Each segment is lowercase snake_case (``^[a-z][a-z0-9_]*$``). This module is
the only place the grammar is defined or validated — everything else calls
:func:`parse` and :func:`compose`.

Validation rejects; it never normalizes. A segment that would only be valid
after case conversion is an error, not a rename.
"""

from __future__ import annotations

import re
from typing import Final, NamedTuple

from .exceptions import InvalidSegmentError, MalformedIdentifierError

#: The one grammar rule every segment must satisfy.
SEGMENT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")

#: Human-readable form of the full grammar, used in error messages.
GRAMMAR: Final[str] = "kind:namespace.object_name (each segment ^[a-z][a-z0-9_]*$)"

_SEGMENT_NAMES: Final[tuple[str, str, str]] = ("kind", "namespace", "object_name")


class Identifier(NamedTuple):
    """A parsed canonical identifier."""

    kind: str
    namespace: str
    name: str

    def __str__(self) -> str:
        return f"{self.kind}:{self.namespace}.{self.name}"


def validate_segment(segment_name: str, value: str) -> str:
    """
    Validate a single identifier segment against the grammar.

    Args:
        segment_name: Which segment this is (``kind`` / ``namespace`` /
            ``object_name``) — used in the error, never to alter behavior.
        value: The candidate segment value.

    Returns:
        The value, unchanged, if it conforms.

    Raises:
        InvalidSegmentError: If the value violates the grammar. The value is
            never transformed to make it conform.
    """
    if not isinstance(value, str) or not SEGMENT_PATTERN.match(value):
        raise InvalidSegmentError(segment_name, value)
    return value


def compose(kind: str, namespace: str, name: str) -> str:
    """
    Compose a canonical identifier from validated segments.

    Raises:
        InvalidSegmentError: If any segment violates the grammar.
    """
    validate_segment("kind", kind)
    validate_segment("namespace", namespace)
    validate_segment("object_name", name)
    return f"{kind}:{namespace}.{name}"


def parse(identifier: str) -> Identifier:
    """
    Parse a canonical identifier string into its three segments.

    The grammar has exactly three segments — an operation suffix (a fourth
    segment) is malformed by design.

    Raises:
        MalformedIdentifierError: If the string does not have the
            ``kind:namespace.object_name`` shape.
        InvalidSegmentError: If a segment violates the segment grammar.
    """
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

    namespace, name = parts
    for segment_name, value in zip(_SEGMENT_NAMES, (kind, namespace, name)):
        validate_segment(segment_name, value)

    return Identifier(kind=kind, namespace=namespace, name=name)
