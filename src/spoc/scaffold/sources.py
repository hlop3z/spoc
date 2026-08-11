"""
Adapters that turn template-set directories into loaded :class:`TemplateSet`s.

A template set is a directory of files carrying the format they will be emitted
as, plus a manifest declaring its substitution values. Template files take a
``.tmpl`` suffix so the repo's own linter and type checker never try to analyze a
half-written module full of placeholders; the suffix is meaningless to the
kernel and is stripped by the manifest's declared targets.

Downstream frameworks register their own sets through the entry-point group
below, which is why an `init` command can be had without reimplementing one.
"""

import tomllib
from dataclasses import replace
from importlib import metadata, resources
from importlib.resources.abc import Traversable
from pathlib import Path
from types import ModuleType

from .archive import extract_archive
from .core import parse_reference
from .errors import IncompleteTemplateSetError, TemplateSetNotFoundError
from .plan import (
    Cache,
    Fetcher,
    Reference,
    ReferenceKind,
    RevisionResolver,
    TemplateFile,
    TemplateSet,
)

#: Entry-point group a downstream framework registers its template sets under.
#: Each entry point resolves to a directory path or an importable package
#: containing ``manifest.toml``.
ENTRY_POINT_GROUP = "spoc.scaffold_templates"

MANIFEST_NAME = "manifest.toml"

#: The set used when an operation names none.
BUILTIN_SET = "default"

#: Every set that ships inside the distribution, resolvable by bare name.
BUILTIN_SETS = frozenset({BUILTIN_SET, "starter"})


def _parse_manifest(manifest_text: str, root: Path) -> TemplateSet:
    """Build a template set from its manifest and the files beside it."""
    try:
        data = tomllib.loads(manifest_text)
    except tomllib.TOMLDecodeError as exc:  # pragma: no cover - malformed set
        raise IncompleteTemplateSetError(f"a readable {MANIFEST_NAME} ({exc})") from exc

    meta = data.get("template_set")
    if not isinstance(meta, dict):
        raise IncompleteTemplateSetError("a [template_set] table")

    name = meta.get("name")
    if not isinstance(name, str) or not name:
        raise IncompleteTemplateSetError("template_set.name")

    values = meta.get("values")
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise IncompleteTemplateSetError("template_set.values")

    entries = data.get("files")
    if not isinstance(entries, list) or not entries:
        raise IncompleteTemplateSetError("at least one [[files]] entry")

    files: list[TemplateFile] = []
    for entry in entries:
        source = entry.get("source")
        target = entry.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            raise IncompleteTemplateSetError("a [[files]] source/target pair")

        path = root / source
        if not path.is_file():
            raise IncompleteTemplateSetError(f"the template file {source}")

        files.append(
            TemplateFile(
                source=source,
                target=target,
                content=path.read_text(encoding="utf-8"),
                per_kind=bool(entry.get("per_kind", False)),
            )
        )

    return TemplateSet(name=name, values=tuple(values), files=tuple(files))


def load_from_directory(root: Path) -> TemplateSet:
    """Load a template set from a directory containing a manifest."""
    manifest = root / MANIFEST_NAME
    if not manifest.is_file():
        raise IncompleteTemplateSetError(f"{MANIFEST_NAME} in {root}")
    return _parse_manifest(manifest.read_text(encoding="utf-8"), root)


def load_from_traversable(root: Traversable) -> TemplateSet:
    """Load a template set from an importable location.

    ``as_file`` is what makes this work when the distribution is not a plain
    directory on disk — a zipped install materializes the tree for the duration
    of the block. Everything a template set holds is read eagerly inside it, so
    nothing survives the context needing a path that has gone away.
    """
    with resources.as_file(root) as path:
        return load_from_directory(path)


def _builtin_traversable(name: str) -> Traversable:
    """A built-in template set's location, however this package is installed."""
    return resources.files("spoc.scaffold") / "templates" / name


def _entry_points() -> dict[str, metadata.EntryPoint]:
    """Template sets registered by downstream frameworks, by name."""
    try:
        found = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception:  # pragma: no cover - defensive against metadata backends
        return {}
    return {ep.name: ep for ep in found}


class RemoteTemplateSource:
    """
    Loads a template set that has to be retrieved before it can be read.

    Composed of the three retrieval ports rather than doing any of their work:
    resolve the reference to an exact revision, serve it from the cache if it is
    retained, otherwise retrieve, admit, and retain it — then load the result as
    an ordinary directory. Everything after ``load_from_directory`` is identical
    to a local set, which is the point: origin buys no special treatment.
    """

    def __init__(
        self, *, revisions: RevisionResolver, fetcher: Fetcher, cache: Cache
    ) -> None:
        self._revisions = revisions
        self._fetcher = fetcher
        self._cache = cache

    def load(self, reference: Reference) -> TemplateSet:
        revision = self._revisions.resolve(reference)

        retained = self._cache.retained(revision)
        if retained is None:
            retained = self._cache.retain(
                revision, lambda staging: self._populate(reference, revision, staging)
            )

        loaded = load_from_directory(_within(retained, reference))
        # The set now knows where it came from, so provenance is a property of
        # what was loaded rather than something the caller has to reconstruct.
        return replace(loaded, reference=reference.raw, revision=revision)

    def _populate(self, reference: Reference, revision: str, staging: Path) -> None:
        """Retrieve and admit one revision into a staging directory."""
        extract_archive(self._fetcher.fetch(reference, revision), staging)


def _within(retained: Path, reference: Reference) -> Path:
    """Resolve the subdirectory a reference named, if it named one.

    Archives from a forge wrap everything in a single top-level directory whose
    name carries the revision. That wrapper is an artifact of the transport, not
    part of the template set, so it is stepped through rather than made the
    author's problem.
    """
    root = retained
    entries = [entry for entry in root.iterdir() if not entry.name.startswith(".")]
    if (
        len(entries) == 1
        and entries[0].is_dir()
        and not (root / MANIFEST_NAME).is_file()
    ):
        root = entries[0]

    if reference.subdirectory:
        candidate = root / reference.subdirectory
        # The subdirectory came from the caller's own reference, but it still
        # reaches the filesystem as a path, so it is contained like any other.
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise TemplateSetNotFoundError(reference.raw, ())
        if not resolved.is_dir():
            raise IncompleteTemplateSetError(
                f"the subdirectory {reference.subdirectory!r} in {reference.raw!r}"
            )
        return resolved

    return root


class InstalledTemplateSources:
    """
    Resolves any template set reference, dispatching on the form it designates.

    Implements the :class:`~spoc.scaffold.plan.EnumerableSource` port.

    Resolution is scheme-first and total: the reference's own form decides which
    kind of source is consulted, before anything is looked up. That ordering is
    the contract — a reference that designates one kind must never fall through
    to another because the first came up empty, or a mistyped scheme ends up
    reported as a missing directory nobody named.

    ``available()`` lists only what can genuinely be enumerated. A remote
    reference has no candidate set, so none is invented for it.
    """

    def __init__(self, remote: RemoteTemplateSource | None = None) -> None:
        self._remote = remote

    def available(self) -> tuple[str, ...]:
        names = {*BUILTIN_SETS, *_entry_points()}
        return tuple(sorted(names))

    def load(self, name: str) -> TemplateSet:
        reference = parse_reference(name)

        match reference.kind:
            case ReferenceKind.PATH:
                loaded = load_from_directory(Path(reference.location))
            case ReferenceKind.REMOTE:
                return self._load_remote(reference)
            case _:
                loaded = self._load_name(reference)

        # A local set cannot move, so it records the reference but no revision.
        return replace(loaded, reference=reference.raw)

    def _load_remote(self, reference: Reference) -> TemplateSet:
        if self._remote is None:
            raise TemplateSetNotFoundError(reference.raw, self.available())
        return self._remote.load(reference)

    def _load_name(self, reference: Reference) -> TemplateSet:
        name = reference.location
        if name in BUILTIN_SETS:
            return load_from_traversable(_builtin_traversable(name))

        entry = _entry_points().get(name)
        if entry is None:
            raise TemplateSetNotFoundError(name, self.available())

        target = entry.load()
        # The group's contract is "a directory path or an importable package".
        # A package is resolved through importlib.resources rather than
        # stringified — str(module) is its repr, which is not a path.
        if isinstance(target, ModuleType):
            return load_from_traversable(resources.files(target))

        root = target if isinstance(target, Path) else Path(str(target))
        if not root.is_dir():
            raise TemplateSetNotFoundError(name, self.available())
        return load_from_directory(root)
