"""
The scaffolding operation itself.

Pure orchestration: it takes the ports as arguments rather than constructing
them, so the whole operation is testable without a filesystem and callable from
a downstream framework's own entry point without going through argv. Concrete
adapters are wired in :mod:`spoc.scaffold.cli`.
"""

from .core import build_plan, detect_conflicts, validate_name
from .errors import TargetNotEmptyError
from .plan import GenerationPlan, ProjectSink, TemplateSource

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
    }

    plan = build_plan(loaded, values, kinds)

    if not sink.is_empty():
        raise TargetNotEmptyError(sink.location())
    detect_conflicts(plan, sink.existing(plan.paths))

    sink.commit(plan)
    return plan
