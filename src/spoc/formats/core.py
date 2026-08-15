"""
The codec port and the format registry — pure, and the only place dispatch happens.

A :class:`Codec` declares one format: what it is called, which extensions it answers to, and
a **lazy factory per direction**. Nothing is imported until a direction is actually used, so
importing this package never pulls in ruamel.yaml or xmltodict, and a project that installed
no extras still reads every standard-library format.

The two directions are declared separately because they genuinely differ — stdlib ``tomllib``
reads TOML and nothing in the standard library writes it. Modelling that as two independent
factories, rather than one codec with a special case, is what lets "TOML output needs
``spoc[toml]``" be a lookup instead of a branch in calling code.

This module imports nothing outside the standard library and the surface's own error base.
The codecs themselves live in ``codecs.py``; the registry is assembled in ``__init__.py``,
which is this package's composition root.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from .errors import (
    MissingDependencyError,
    UnknownFormatError,
    UnsupportedDirectionError,
)

#: A decoder takes the source text plus any format-specific options; an encoder takes the
#: value. Both speak only the JSON data model on the representation side (design.md D1).
DecodeFn = Callable[..., Any]
EncodeFn = Callable[..., str]

READ: Final[str] = "read"
WRITE: Final[str] = "write"


@dataclass(frozen=True)
class Codec:
    """One format's declaration: its names, and a lazy factory per direction."""

    name: str
    extensions: tuple[str, ...]
    reader: Callable[[], DecodeFn] | None = None
    writer: Callable[[], EncodeFn] | None = None
    read_extra: str | None = None
    write_extra: str | None = None

    def factory(self, direction: str) -> Callable[[], Any] | None:
        return self.reader if direction == READ else self.writer

    def extra(self, direction: str) -> str | None:
        return self.read_extra if direction == READ else self.write_extra


@dataclass(frozen=True)
class FormatSupport:
    """What one format can do *in the current environment*."""

    name: str
    extensions: tuple[str, ...]
    can_read: bool
    can_write: bool


class FormatRegistry:
    """Codecs keyed by name and by extension, settled on first use and cached.

    Settled, not merely resolved: the first probe of a direction records whether
    it is available *or* unavailable, so neither answer is derived twice.
    """

    def __init__(self, codecs: tuple[Codec, ...]) -> None:
        self._codecs: dict[str, Codec] = {c.name: c for c in codecs}
        self._by_extension: dict[str, Codec] = {
            ext: c for c in codecs for ext in c.extensions
        }
        self._resolved: dict[tuple[str, str], Any] = {}
        # The other half of the same answer: which directions were probed and
        # found unavailable, holding the extra their failure names. Python does
        # not cache a *failed* import, so without this every repeat probe re-walks
        # every path finder — and `supported()` probes two directions per codec.
        self._unavailable: dict[tuple[str, str], str] = {}

    @property
    def names(self) -> tuple[str, ...]:
        """Every declared format name, ordered."""
        return tuple(sorted(self._codecs))

    def codec(self, name: str) -> Codec:
        """The declaration for one format."""
        if name not in self._codecs:
            raise UnknownFormatError(name, self.names)
        return self._codecs[name]

    def for_extension(self, extension: str) -> Codec:
        """The declaration answering to a file extension, including the dot."""
        key = extension.lower()
        if key not in self._by_extension:
            raise UnknownFormatError(key, tuple(sorted(self._by_extension)))
        return self._by_extension[key]

    def function(self, name: str, direction: str) -> Any:
        """Resolve one direction of one format, importing its dependency if needed.

        Availability is settled on first probe and holds for the life of the
        process, failure as much as success: a dependency installed while this
        process runs is observed by the next one, not this one. That is the same
        rule every other import in the process already follows, and the price of
        not re-running discovery that has already answered.
        """
        key = (name, direction)
        cached = self._resolved.get(key)
        if cached is not None:
            return cached
        settled = self._unavailable.get(key)
        if settled is not None:
            # Raised fresh rather than stored and re-raised: one exception object
            # shared across call sites accumulates their tracebacks.
            raise MissingDependencyError(f"{direction} {name!r}", settled)

        codec = self.codec(name)
        factory = codec.factory(direction)
        if factory is None:
            # Not cached: it is a dict lookup on the declaration, imports nothing,
            # and cannot change. There is nothing here to avoid repeating.
            raise UnsupportedDirectionError(name, direction)
        try:
            resolved = factory()
        except ImportError as exc:
            extra = codec.extra(direction)
            if extra is None:  # a standard-library codec failing to import is a defect
                raise  # never cached — a defect must resurface with its own traceback
            self._unavailable[key] = extra
            raise MissingDependencyError(f"{direction} {name!r}", extra) from exc

        self._resolved[key] = resolved
        return resolved

    def supported(self) -> tuple[FormatSupport, ...]:
        """Every format with the directions currently available, probed not assumed."""
        return tuple(
            FormatSupport(
                name=codec.name,
                extensions=codec.extensions,
                can_read=self._available(codec.name, READ),
                can_write=self._available(codec.name, WRITE),
            )
            for codec in (self._codecs[n] for n in self.names)
        )

    def _available(self, name: str, direction: str) -> bool:
        try:
            self.function(name, direction)
        except (MissingDependencyError, UnsupportedDirectionError):
            return False
        return True
