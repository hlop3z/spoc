"""
The operations: read and write one source, or collect a whole tree.

Every function here takes the registry rather than reaching for a module-level one, so this
module holds no state and ``__init__.py`` stays the single composition root — the same
arrangement ``framework.py`` uses for the kernel.

Collection is eager by decision, not by omission (design.md D4). A tree is fully parsed before
it is returned, and one malformed file fails the whole call, so a typo surfaces where the
collection was requested instead of wherever some later code path first read that key.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.identity import validate_segment
from .core import READ, WRITE, FormatRegistry
from .errors import (
    CollectionError,
    DuplicateEntryError,
    FormatError,
    UnknownFormatError,
)

# ── One source ────────────────────────────────────────────────────────────


def loads(registry: FormatRegistry, text: str, format: str, **options: Any) -> Any:
    """Decode `text` in the named format into the representation."""
    return registry.function(format, READ)(text, **options)


def dumps(registry: FormatRegistry, value: Any, format: str, **options: Any) -> str:
    """Encode a representation value as text in the named format."""
    return registry.function(format, WRITE)(value, **options)


def read(
    registry: FormatRegistry,
    path: Path | str,
    *,
    format: str | None = None,
    **options: Any,
) -> Any:
    """Read a file, inferring the format from its extension unless one is given."""
    source = Path(path)
    name = format or registry.for_extension(source.suffix).name
    return loads(registry, source.read_text(encoding="utf-8"), name, **options)


def write(
    registry: FormatRegistry,
    value: Any,
    path: Path | str,
    *,
    format: str | None = None,
    **options: Any,
) -> Path:
    """Write a representation value to a file, inferring the format from its extension."""
    target = Path(path)
    name = format or registry.for_extension(target.suffix).name
    target.write_text(dumps(registry, value, name, **options), encoding="utf-8")
    return target


# ── A whole tree ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Collection(Mapping[str, Any]):
    """One mapping of every collected entry, plus what was skipped getting there."""

    entries: dict[str, Any] = field(default_factory=dict)
    skipped: tuple[str, ...] = ()

    def __getitem__(self, key: str) -> Any:
        return self.entries[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)


def derive_key(root: Path, source: Path) -> str:
    """The entry key for a file: its location, dotted, under the kernel's grammar (D8)."""
    relative = source.relative_to(root)
    segments = [*relative.parts[:-1], relative.stem]
    for segment in segments:
        validate_segment("collection key segment", segment)
    return ".".join(segments)


def collect(
    registry: FormatRegistry,
    root: Path | str,
    *,
    options: Mapping[str, Mapping[str, Any]] | None = None,
) -> Collection:
    """Read every supported file under `root` into one mapping, eagerly."""
    base = Path(root)
    if not base.is_dir():
        return Collection()

    per_format = options or {}
    entries: dict[str, Any] = {}
    origins: dict[str, Path] = {}
    skipped: list[str] = []

    for source in sorted(p for p in base.rglob("*") if p.is_file()):
        try:
            codec = registry.for_extension(source.suffix)
        except UnknownFormatError:
            skipped.append(str(source))
            continue

        key = derive_key(base, source)
        if key in origins:
            raise DuplicateEntryError(key, str(origins[key]), str(source))

        try:
            entries[key] = read(
                registry, source, format=codec.name, **per_format.get(codec.name, {})
            )
        except FormatError:
            raise
        except Exception as exc:
            raise CollectionError(str(source), f"{type(exc).__name__}: {exc}") from exc

        origins[key] = source

    return Collection(entries=entries, skipped=tuple(skipped))
