"""
The pure core of the scaffolder: validate, plan, detect conflicts.

No filesystem, no argv, no imports beyond the standard library and the kernel's
own identity grammar. Everything here is a function from values to a plan, which
is what lets the whole operation be checked before a byte is written.

Substitution uses :class:`string.Template`, deliberately. It performs name
substitution and nothing else — no expressions, no conditionals, no evaluation —
which is exactly the contract the template specs require. Its
``get_identifiers()`` is how a set's placeholders are enumerated without
rendering.
"""

from string import Template

from ..core.identity import validate_segment
from .errors import (
    IncompleteTemplateSetError,
    PathConflictError,
    PathEscapeError,
    UndeclaredValueError,
    UnsatisfiedValueError,
)
from .plan import GenerationPlan, PlannedFile, TemplateSet, Values

#: Names that must never appear in a path segment the user supplies. Traversal
#: is rejected here, in the pure layer, so it cannot depend on a filesystem
#: check that a symlink could defeat.
_UNSAFE_FRAGMENTS = ("..", "/", "\\", ":")

#: The value bound once per kind while rendering a ``per_kind`` template. It is a
#: declared substitution value like any other, but it is supplied by the
#: repetition rather than by the caller — so validation counts it as satisfied.
PER_KIND_VALUE = "kind"


def validate_name(segment_name: str, value: str) -> str:
    """
    Validate a user-supplied name against the kernel's identity grammar.

    The grammar is the kernel's, not the scaffolder's — a generated project must
    be one the kernel would accept, so there is one definition of a legal name.

    Raises:
        InvalidSegmentError: If the value violates the grammar.
        PathEscapeError: If the value could escape the destination root.
    """
    if any(fragment in value for fragment in _UNSAFE_FRAGMENTS):
        raise PathEscapeError(value)
    return validate_segment(segment_name, value)


def declared_identifiers(template_set: TemplateSet) -> tuple[str, ...]:
    """
    Every placeholder the set's templates actually use, in stable order.

    Read straight from the template text — this is the check that the manifest's
    declaration is honest, not a restatement of it.
    """
    found: list[str] = []
    for file in template_set.files:
        for text in (file.content, file.target):
            for name in Template(text).get_identifiers():
                if name not in found:
                    found.append(name)
    return tuple(found)


def validate_template_set(template_set: TemplateSet, values: Values) -> None:
    """
    Check a template set is complete and renderable before anything is written.

    Two directions, both required:

    - every placeholder a template uses must be declared in the manifest, so the
      declaration can be trusted without rendering;
    - every declared value must be supplied, either by this operation or by the
      per-kind repetition.

    Raises:
        IncompleteTemplateSetError: The set has no files at all.
        UndeclaredValueError: A template uses an undeclared placeholder.
        UnsatisfiedValueError: A declared value was not supplied.
    """
    if not template_set.files:
        raise IncompleteTemplateSetError("any template file")

    declared = set(template_set.values)
    for file in template_set.files:
        for text in (file.content, file.target):
            for name in Template(text).get_identifiers():
                if name not in declared:
                    raise UndeclaredValueError(name, file.source)

    supplied = set(values) | {PER_KIND_VALUE}
    for name in template_set.values:
        if name not in supplied:
            raise UnsatisfiedValueError(name)


def _render(text: str, values: Values) -> str:
    """Substitute declared values, leaving nothing to evaluate."""
    return Template(text).substitute(values)


def build_plan(
    template_set: TemplateSet,
    values: Values,
    kinds: tuple[str, ...],
) -> GenerationPlan:
    """
    Render a template set into an ordered, immutable plan.

    A template marked ``per_kind`` is emitted once for each declared kind, with
    ``kind`` bound to that kind for both its content and its destination path.
    The repetition is declared by the manifest, not expressed inside a template —
    template content stays free of logic.

    Raises:
        UndeclaredValueError / UnsatisfiedValueError: via validation.
        PathEscapeError: If a rendered destination escapes the root.
    """
    validate_template_set(template_set, values)

    planned: list[PlannedFile] = []
    for file in template_set.files:
        bindings = (
            [{**values, PER_KIND_VALUE: kind} for kind in kinds]
            if file.per_kind
            else [dict(values)]
        )
        for binding in bindings:
            path = _render(file.target, binding)
            _reject_escape(path)
            planned.append(
                PlannedFile(path=path, content=_render(file.content, binding))
            )

    return GenerationPlan(files=tuple(planned))


def _reject_escape(path: str) -> None:
    """Refuse a rendered destination that climbs out of the root."""
    if path.startswith(("/", "\\")) or ".." in path.split("/"):
        raise PathEscapeError(path)


def detect_conflicts(plan: GenerationPlan, existing: tuple[str, ...]) -> None:
    """
    Refuse a plan that would overwrite content the scaffolder did not create.

    Pure: the caller supplies what exists, so this stays a comparison rather than
    a filesystem query.

    Raises:
        PathConflictError: Naming the first conflicting path.
    """
    collisions = sorted(set(plan.paths) & set(existing))
    if collisions:
        raise PathConflictError(collisions[0])
