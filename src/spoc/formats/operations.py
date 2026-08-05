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

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Final

from .core import READ, WRITE, FormatRegistry
from .errors import (
    CollectionError,
    DuplicateEntryError,
    EncodeError,
    FormatError,
    MissingDependencyError,
    UnknownFormatError,
)

# ── One source ────────────────────────────────────────────────────────────


def loads(registry: FormatRegistry, text: str, format: str, **options: Any) -> Any:
    """Decode `text` in the named format into the representation."""
    return registry.function(format, READ)(text, **options)


def dumps(registry: FormatRegistry, value: Any, format: str, **options: Any) -> str:
    """Encode a representation value as text in the named format.

    A value the target format cannot express fails inside the ``FormatError``
    family naming the format, rather than as whichever exception the underlying
    serializer happens to raise — the caller writes one ``except``, not one per
    adopted library.
    """
    encode = registry.function(format, WRITE)
    try:
        return encode(value, **options)
    except FormatError:
        raise
    except Exception as exc:
        raise EncodeError(format, f"{type(exc).__name__}: {exc}") from exc


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
    """Write a representation value to a file, inferring the format from its extension.

    Parent directories are created as needed: the caller named where the file
    goes, and failing on the directory above it would only make them write the
    same two lines everywhere.
    """
    target = Path(path)
    name = format or registry.for_extension(target.suffix).name
    text = dumps(registry, value, name, **options)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
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


#: The collection-key segment grammar — the same lowercase snake_case
#: convention the SPOC kernel uses for identifier segments, restated here
#: because the two distributions share a convention, never code.
_SEGMENT: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")


def derive_key(root: Path, source: Path) -> str:
    """The entry key for a file: its location, dotted, one grammar per segment (D8)."""
    relative = source.relative_to(root)
    segments = [*relative.parts[:-1], relative.stem]
    for segment in segments:
        if not _SEGMENT.match(segment):
            raise CollectionError(
                str(source),
                f"key segment {segment!r} must match ^[a-z][a-z0-9_]*$ "
                "(lowercase snake_case)",
            )
    return ".".join(segments)


def _is_ignored(relative: Path, ignore: tuple[str, ...]) -> bool:
    """True if any segment of `relative` is hidden or matches an ignore pattern."""
    return any(
        segment.startswith(".") or any(fnmatch(segment, p) for p in ignore)
        for segment in relative.parts
    )


def collect(
    registry: FormatRegistry,
    root: Path | str,
    *,
    options: Mapping[str, Mapping[str, Any]] | None = None,
    ignore: tuple[str, ...] = (),
) -> Collection:
    """Read every supported file under `root` into one mapping, eagerly.

    An empty directory is a valid (empty) collection; an absent one is a typo
    and fails loudly, like every other way a collection can go wrong.

    Hidden entries — any path segment starting with ``.`` — are skipped, as are
    those matching an `ignore` glob. Skipping happens *before* a key is derived,
    so a tool's own directory (``.cache``, ``.git``) can neither contribute
    entries nor fail the collection on a key segment it was never going to use.
    What is actually collected stays loud: a non-conforming key in a directory
    that was not skipped still fails the whole call.
    """
    base = Path(root)
    if not base.is_dir():
        raise CollectionError(str(base), "not a directory")

    per_format = options or {}
    entries: dict[str, Any] = {}
    origins: dict[str, Path] = {}
    skipped: list[str] = []

    for source in sorted(p for p in base.rglob("*") if p.is_file()):
        if _is_ignored(source.relative_to(base), ignore):
            skipped.append(str(source))
            continue

        try:
            codec = registry.for_extension(source.suffix)
        except UnknownFormatError:
            skipped.append(str(source))
            continue

        # derive_key fails inside the FormatError family: a caller watching
        # `except FormatError` sees every way a collection can go wrong,
        # key grammar included.
        key = derive_key(base, source)
        if key in origins:
            raise DuplicateEntryError(key, str(origins[key]), str(source))

        try:
            entries[key] = read(
                registry, source, format=codec.name, **per_format.get(codec.name, {})
            )
        except MissingDependencyError:
            raise  # the actionable fact is the missing extra, not the path
        except FormatError as exc:
            # A decode failure names its format; the collection contract owes
            # the caller the path it came from.
            raise CollectionError(str(source), str(exc)) from exc
        except Exception as exc:
            raise CollectionError(str(source), f"{type(exc).__name__}: {exc}") from exc

        origins[key] = source

    return Collection(entries=entries, skipped=tuple(skipped))
