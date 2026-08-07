"""
The scaffolding operation itself.

Pure orchestration: it takes the ports as arguments rather than constructing
them, so the whole operation is testable without a filesystem and callable from
a downstream framework's own entry point without going through argv. Concrete
adapters are wired in :mod:`spoc.scaffold.cli`.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from string import Template

from .core import build_plan, detect_conflicts, validate_name
from .errors import IncompleteTemplateSetError, TargetNotEmptyError
from .plan import GenerationPlan, PlannedFile, ProjectSink, TemplateSource
from .provenance import Origin, describe_divergence

#: What a project gets when the caller does not say otherwise. Two kinds, so the
#: generated project shows a registry with more than one facet in it. No
#: dependency ordering is declared: a scaffold should not invent an architecture,
#: and `dependencies=` is one line to add once the author knows they want it.
DEFAULT_KINDS: tuple[str, ...] = ("models", "views")

DEFAULT_APP_NAME = "core"


def init_project(
    *,
    source: TemplateSource,
    sink: ProjectSink,
    project_name: str,
    app_name: str = DEFAULT_APP_NAME,
    kinds: tuple[str, ...] = DEFAULT_KINDS,
    template_set: str = "default",
) -> GenerationPlan:
    """
    Generate a runnable project.

    Every failure raises before ``sink.commit`` is reached, so a raised error
    means nothing was written.

    Args:
        source: Where template sets come from.
        sink: Where the plan is written.
        project_name: Name of the project; must satisfy the identity grammar.
        app_name: Name of the starter app.
        kinds: The kinds the generated framework declares.
        template_set: Which template set to render.

    Returns:
        The plan that was committed.

    Raises:
        InvalidSegmentError / PathEscapeError: A supplied name is not legal.
        TemplateSetNotFoundError / IncompleteTemplateSetError: Bad template set.
        TargetNotEmptyError / PathConflictError: The destination is occupied.
    """
    validate_name("project_name", project_name)
    validate_name("app_name", app_name)
    if not kinds:
        raise ValueError("A framework must declare at least one kind")
    for kind in kinds:
        validate_name("kind", kind)

    loaded = source.load(template_set)

    values = {
        "project_name": project_name,
        "app_name": app_name,
        "kinds_args": ", ".join(f'"{kind}"' for kind in kinds),
        "kind_decorators": "\n".join(
            f'{kind} = framework.kind("{kind}")' for kind in kinds
        ),
        # The origin record's values. Supplied for every generation, whatever the
        # set's origin, so the comparison a later `add_app` makes is always
        # possible rather than possible only for remote sets.
        "template_reference": loaded.reference or template_set,
        "template_revision": loaded.revision,
        "template_set_name": loaded.name,
    }

    plan = build_plan(loaded, values, kinds)

    if not sink.is_empty():
        raise TargetNotEmptyError(sink.location())
    detect_conflicts(plan, sink.existing(plan.paths))

    sink.commit(plan)
    return plan


#: Marks the templates that shape an app: any file whose destination is
#: parameterized by the app's name. The manifest already draws this line —
#: no second declaration is invented for it.
APP_MARKER = "$app_name"


@dataclass(frozen=True)
class AddedApp:
    """What `add_app` did: the files written (paths relative to `app_dir`),
    where the app landed, the dotted reference that installs it, and anything
    the caller should be told about the project it landed in."""

    plan: GenerationPlan
    app_dir: str
    config_reference: str
    divergence: str | None = None
    """Set when the rendered template set differs from the project's recorded
    origin, or when the project records none. Never a reason to fail."""


def add_app(
    *,
    source: TemplateSource,
    sink_factory: Callable[[str], ProjectSink],
    app_name: str,
    kinds: tuple[str, ...],
    template_set: str = "default",
    read_origin: Callable[[], Origin | None] | None = None,
) -> AddedApp:
    """
    Generate one additional app into an existing project.

    The selected template set's app-shaped files (those whose targets carry
    ``$app_name``) are rendered exactly as project generation renders them,
    then committed under the app's own directory — so the never-overwrite
    guarantee falls out of the sink's existing contract: an app that already
    exists is refused with nothing written.

    The project's configuration is never edited. The returned
    ``config_reference`` is the dotted path the author adds to a mode list
    under ``[spoc.apps]`` — stating it is the caller's (CLI's) job.

    Raises:
        InvalidSegmentError: A supplied name is not legal.
        TemplateSetNotFoundError / IncompleteTemplateSetError: Bad template
            set, or one with no app-shaped files.
        TargetNotEmptyError: The app already exists.
    """
    validate_name("app_name", app_name)
    if not kinds:
        raise ValueError("An app must be generated for at least one kind")
    for kind in kinds:
        validate_name("kind", kind)

    loaded = source.load(template_set)
    app_files = tuple(f for f in loaded.files if APP_MARKER in f.target)
    if not app_files:
        raise IncompleteTemplateSetError(
            f"app templates (targets containing {APP_MARKER!r}) in set {loaded.name!r}"
        )

    # The subset re-declares only what its own files use, so the set-level
    # invariant (declared ⇔ supplied) keeps holding for the narrowed set.
    used = {
        name
        for file in app_files
        for text in (file.content, file.target)
        for name in Template(text).get_identifiers()
    }
    subset = replace(loaded, files=app_files, values=tuple(sorted(used)))
    plan = build_plan(subset, {"app_name": app_name}, kinds)

    # The app directory is the deepest path prefix every rendered file shares;
    # rebasing the plan onto it scopes the commit — and its refusals — to the
    # one directory this operation may create.
    split_paths = [planned.path.split("/") for planned in plan.files]
    depth = min(len(parts) - 1 for parts in split_paths)
    common: list[str] = []
    for level in range(depth):
        names = {parts[level] for parts in split_paths}
        if len(names) != 1:
            break
        common.append(names.pop())
    if not common:
        raise IncompleteTemplateSetError(
            f"a common app directory in set {loaded.name!r}'s app templates"
        )

    app_dir = "/".join(common)
    rebased = GenerationPlan(
        tuple(
            PlannedFile(path="/".join(parts[len(common) :]), content=planned.content)
            for parts, planned in zip(split_paths, plan.files, strict=True)
        )
    )

    # Compared before writing so the report describes what is about to happen,
    # but never able to prevent it: a project may legitimately draw from more
    # than one template set.
    divergence = (
        describe_divergence(
            read_origin(),
            Origin(
                reference=loaded.reference or template_set,
                revision=loaded.revision,
                set_name=loaded.name,
            ),
        )
        if read_origin is not None
        else None
    )

    sink = sink_factory(app_dir)
    sink.commit(rebased)  # refuses a non-empty destination itself
    return AddedApp(
        plan=rebased,
        app_dir=app_dir,
        config_reference=app_dir.replace("/", "."),
        divergence=divergence,
    )
