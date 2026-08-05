"""
``spoc_formats`` — read, write, collect, and address structured data.

Five formats normalize to one representation drawn from the JSON data model, and everything
else is expressed against that: ``Any Format → JSON → Any Format``. JSON, CSV, and TOML
*reading* are standard library and work on a bare install; YAML, XML, and TOML *writing* live
behind extras and say so when they are missing.

    import spoc_formats as formats

    settings = formats.read("config/app.yaml")
    data = formats.collect("data")            # a tree of mixed formats, one mapping
    port = formats.pointer(settings, "/server/port")      # exact — raises if absent
    live = formats.query(data["users"], "$[?@.active == true].email")   # query — may be empty

This is its own distribution, sharing a repository with the SPOC kernel and
nothing else: neither package imports the other, and either installs alone.
Nothing here is invoked by ``Framework.start`` — reading ``spoc.toml`` remains
the kernel's own job through stdlib ``tomllib``.

This module is the composition root. It owns the one registry; everything else takes it as an
argument and holds no state.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import operations as _ops
from .access import pointer, query
from .codecs import CODECS
from .core import Codec, FormatRegistry, FormatSupport
from .errors import (
    CollectionError,
    DuplicateEntryError,
    FormatError,
    MissingDependencyError,
    PointerResolutionError,
    UnknownFormatError,
    UnsupportedDirectionError,
)
from .operations import Collection

#: The one registry. Codecs resolve on first use, so importing this loads no extra.
REGISTRY: FormatRegistry = FormatRegistry(CODECS)


def loads(text: str, format: str, **options: Any) -> Any:
    """Decode `text` in the named format into the representation."""
    return _ops.loads(REGISTRY, text, format, **options)


def dumps(value: Any, format: str, **options: Any) -> str:
    """Encode a representation value as text in the named format."""
    return _ops.dumps(REGISTRY, value, format, **options)


def read(path: Path | str, *, format: str | None = None, **options: Any) -> Any:
    """Read a file, inferring the format from its extension unless one is given."""
    return _ops.read(REGISTRY, path, format=format, **options)


def write(
    value: Any, path: Path | str, *, format: str | None = None, **options: Any
) -> Path:
    """Write a representation value to a file, inferring the format from its extension."""
    return _ops.write(REGISTRY, value, path, format=format, **options)


def collect(
    root: Path | str, *, options: Mapping[str, Mapping[str, Any]] | None = None
) -> Collection:
    """Read every supported file under `root` into one mapping, eagerly."""
    return _ops.collect(REGISTRY, root, options=options)


def supported() -> tuple[FormatSupport, ...]:
    """Every format with the directions available *in this environment*."""
    return REGISTRY.supported()


__all__ = [
    # Reading and writing
    "loads",
    "dumps",
    "read",
    "write",
    # Collection
    "collect",
    "Collection",
    # Addressing
    "pointer",
    "query",
    # Introspection
    "supported",
    "FormatSupport",
    "Codec",
    "FormatRegistry",
    "REGISTRY",
    # Errors
    "FormatError",
    "UnknownFormatError",
    "MissingDependencyError",
    "UnsupportedDirectionError",
    "DuplicateEntryError",
    "CollectionError",
    "PointerResolutionError",
]
