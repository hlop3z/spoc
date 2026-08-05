"""
The generation plan and the ports the core talks to.

A plan is the whole output of a scaffolding operation, computed and validated
before anything touches a filesystem. This is what makes "nothing is written on
failure" structural rather than aspirational: a plan that cannot be fully
realized is never handed to a sink.

The core names these ports; the adapters depend on them. Nothing here imports
anything outside the standard library.
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
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


class TemplateSource(Protocol):
    """Yields template sets by name."""

    def load(self, name: str) -> TemplateSet:
        """Return the named template set, or raise TemplateSetNotFoundError."""
        ...

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


Values = Mapping[str, str]
