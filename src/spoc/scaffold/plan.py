"""
The generation plan and the ports the core talks to.

A plan is the whole output of a scaffolding operation, computed and validated
before anything touches a filesystem. This is what makes "nothing is written on
failure" structural rather than aspirational: a plan that cannot be fully
realized is never handed to a sink.

The core names these ports; the adapters depend on them. Nothing here imports
anything outside the standard library.
"""

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PlannedFile:
    """One file a plan will emit, with its content already rendered."""

    path: str
    """Destination path, relative to the target root, using forward slashes."""

    content: str


@dataclass(frozen=True, slots=True)
class GenerationPlan:
    """
    An immutable, ordered set of files to emit.

    Ordering is preserved so generation is deterministic and diffable; nothing
    in the writing path depends on it.
    """

    files: tuple[PlannedFile, ...]

    def __iter__(self) -> Iterator[PlannedFile]:
        return iter(self.files)

    def __len__(self) -> int:
        return len(self.files)

    @property
    def paths(self) -> tuple[str, ...]:
        """Every destination path this plan would write."""
        return tuple(f.path for f in self.files)


@dataclass(frozen=True, slots=True)
class TemplateFile:
    """One template in a set: where it comes from, where it lands."""

    source: str
    """Identifier of the template within its set — used only in errors."""

    target: str
    """Destination path, itself substitutable."""

    content: str

    per_kind: bool = False
    """When true, this template is emitted once per declared kind."""


@dataclass(frozen=True, slots=True)
class TemplateSet:
    """
    A loaded template set: its declared substitution values and its files.

    ``values`` is the enumerable declaration the spec requires — it can be read
    without rendering anything.
    """

    name: str
    values: tuple[str, ...]
    files: tuple[TemplateFile, ...]

    reference: str = ""
    """The reference this set was resolved from, as the caller spelled it."""

    revision: str = ""
    """The exact revision it resolved to, when it came from somewhere that has
    one. Empty for a set that cannot move — a built-in or a local directory."""


class ReferenceKind(StrEnum):
    """What kind of source a reference designates.

    The kind is decided by the reference's own form, never by what happens to
    exist locally — which is what makes resolution total rather than a chain of
    attempts that fall through to each other.
    """

    NAME = "name"
    """The built-in set, or one registered by an installed distribution."""

    PATH = "path"
    """A directory on the local filesystem."""

    REMOTE = "remote"
    """A location that must be retrieved before it can be loaded."""


@dataclass(frozen=True, slots=True)
class Reference:
    """A parsed template set reference.

    Produced by :func:`spoc.scaffold.core.parse_reference`, which is pure: this
    carries only what the spelling said, never anything learned by looking at a
    disk or a network. Scheme expansion (what ``gh:`` means) is an adapter's job,
    because it constructs a location; deciding that ``gh:`` *is* a remote scheme
    is this layer's job, because it is grammar.
    """

    kind: ReferenceKind

    raw: str
    """The reference exactly as supplied — used in errors, never to resolve."""

    scheme: str
    """The scheme, lowercased, or empty for a bare name or a plain path."""

    location: str
    """The locator with scheme, revision, and fragment stripped."""

    revision: str | None = None
    """The exact revision requested, from ``@ref``."""

    subdirectory: str | None = None
    """Path within the retrieved content, from ``#subdirectory=``."""

    @property
    def is_pinned(self) -> bool:
        """True when the reference names a revision rather than a moving target."""
        return self.revision is not None


class TemplateSource(Protocol):
    """Yields template sets by name."""

    def load(self, name: str) -> TemplateSet:
        """Return the named template set, or raise TemplateSetNotFoundError."""
        ...


class EnumerableSource(TemplateSource, Protocol):
    """A source that can list what it holds.

    Split from :class:`TemplateSource` because a remote resolver cannot answer
    it: there is no set of "all retrievable references". Only sources that
    implement this contribute candidates to a not-found error, so that error
    never lists a set of possibilities it made up.

    Provisional: may change incompatibly in a minor release. It settles when a
    template source outside this package implements it — at which point the
    shape is fixed by a real implementer — or is withdrawn if none appears and
    the not-found error's candidates can be gathered without a second port.
    """

    def available(self) -> tuple[str, ...]:
        """Every template set name this source can load."""
        ...


class ProjectSink(Protocol):
    """Writes a plan, and reports what already exists."""

    def location(self) -> str:
        """Human-readable name of where the plan would land — used in errors."""
        ...

    def existing(self, paths: Sequence[str]) -> tuple[str, ...]:
        """Which of these relative paths already exist at the destination."""
        ...

    def is_empty(self) -> bool:
        """True when the destination is absent or contains nothing."""
        ...

    def commit(self, plan: GenerationPlan) -> None:
        """Write every file in the plan, or none of them. Refuses a non-empty
        destination itself — the guarantee lives here, not in the caller."""
        ...


class RevisionResolver(Protocol):
    """Turns a reference into the exact revision it designates.

    Separate from retrieval because it runs first and unconditionally: a moving
    reference must become an immutable one *before* the cache is consulted, or
    the cache would be keyed by something that moves.
    """

    def resolve(self, reference: Reference) -> str:
        """Return the exact, immutable revision this reference designates."""
        ...


class Fetcher(Protocol):
    """Retrieves the bytes of an exact revision."""

    def fetch(self, reference: Reference, revision: str) -> bytes:
        """Return the archived content of that revision.

        Implementations refuse a redirect onto weaker guarantees than the
        reference carried, and never use a name supplied by the remote party to
        construct a local path.
        """
        ...


class Cache(Protocol):
    """Retains retrieved revisions so a repeat generation retrieves nothing."""

    def retained(self, revision: str) -> Path | None:
        """The directory holding this revision, or None if it is not retained."""
        ...

    def retain(self, revision: str, populate: Callable[[Path], None]) -> Path:
        """Populate a fresh location for this revision and retain it.

        The population runs against a staging location and is only published
        under the revision once it completes, so an interrupted retrieval can
        never leave a half-populated revision looking retained.
        """
        ...


Values = Mapping[str, str]
