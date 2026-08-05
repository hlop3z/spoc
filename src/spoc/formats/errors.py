"""
The data surface's error family.

:class:`FormatError` is the data surface's own root — ``spoc.formats`` imports
nothing from the SPOC kernel and its errors are not kernel errors, so a project
using both catches each family's base separately. Every failure this surface
produces is one of these.

Two of these carry a contract rather than just a message. A format whose optional extra is
absent raises :class:`MissingDependencyError` naming the extra to install, never an
``ImportError`` from a transitive module — otherwise the extras are not optional in practice.
And exact addressing raises :class:`PointerResolutionError` naming the segment that could not
be resolved, mirroring the per-segment precision the SPOC registry's own resolution promises.
"""

from __future__ import annotations


class FormatError(Exception):
    """Base for every data-surface error."""


class UnknownFormatError(FormatError):
    """A format name or file extension maps to no codec."""

    def __init__(self, value: str, supported: tuple[str, ...]) -> None:
        self.value, self.supported = value, supported
        super().__init__(
            f"Unknown format {value!r}. Supported formats: "
            f"{', '.join(supported) or '(none)'}"
        )


class MissingDependencyError(FormatError):
    """A capability is supported, but the extra that enables it is not installed."""

    def __init__(self, capability: str, extra: str) -> None:
        self.capability, self.extra = capability, extra
        super().__init__(
            f"Cannot {capability}: it needs an optional dependency that is not "
            f'installed. Install it with: pip install "spoc[{extra}]"'
        )


class UnsupportedDirectionError(FormatError):
    """A format is known, but cannot be used in the requested direction at all."""

    def __init__(self, format_name: str, direction: str) -> None:
        self.format_name, self.direction = format_name, direction
        super().__init__(
            f"Format {format_name!r} cannot be used to {direction}. No optional "
            "dependency enables this direction — it is unsupported"
        )


class DuplicateEntryError(FormatError):
    """Two collected files derive the same key."""

    def __init__(self, key: str, first: str, second: str) -> None:
        self.key, self.first, self.second = key, first, second
        super().__init__(
            f"Duplicate collection key {key!r}: {first} and {second} derive the same "
            "key. Rename one, or move it — collection never picks a winner"
        )


class CollectionError(FormatError):
    """A file in a collection could not be read, so the whole collection fails."""

    def __init__(self, path: str, reason: str) -> None:
        self.path, self.reason = path, reason
        super().__init__(f"Cannot collect {path}: {reason}")


class PointerResolutionError(FormatError):
    """An exact address named a location that does not exist."""

    def __init__(self, pointer: str, segment: str) -> None:
        self.pointer, self.segment = pointer, segment
        super().__init__(
            f"Pointer {pointer!r} could not be resolved: no value at segment "
            f"{segment!r}. An exact address names one value or fails — use a query "
            "if an empty result is a valid answer"
        )
