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
from importlib import metadata, resources
from importlib.resources.abc import Traversable
from pathlib import Path
from types import ModuleType

from .errors import IncompleteTemplateSetError, TemplateSetNotFoundError
from .plan import TemplateFile, TemplateSet

#: Entry-point group a downstream framework registers its template sets under.
#: Each entry point resolves to a directory path or an importable package
#: containing ``manifest.toml``.
ENTRY_POINT_GROUP = "spoc.scaffold_templates"

MANIFEST_NAME = "manifest.toml"

BUILTIN_SET = "default"


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


def _builtin_traversable() -> Traversable:
    """The built-in template set's location, however this package is installed."""
    return resources.files("spoc.scaffold") / "templates" / BUILTIN_SET


def _entry_points() -> dict[str, metadata.EntryPoint]:
    """Template sets registered by downstream frameworks, by name."""
    try:
        found = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception:  # pragma: no cover - defensive against metadata backends
        return {}
    return {ep.name: ep for ep in found}


class InstalledTemplateSources:
    """
    Resolves template sets from the built-in set plus installed entry points.

    Implements the :class:`~spoc.scaffold.plan.TemplateSource` port.
    """

    def available(self) -> tuple[str, ...]:
        names = {BUILTIN_SET, *_entry_points()}
        return tuple(sorted(names))

    def load(self, name: str) -> TemplateSet:
        if name == BUILTIN_SET:
            return load_from_traversable(_builtin_traversable())

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
