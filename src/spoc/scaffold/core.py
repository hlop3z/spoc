"""
The pure core of the scaffolder: validate, plan, detect conflicts.

No filesystem, no argv, no imports beyond the standard library and the kernel's
own identity grammar. Everything here is a function from values to a plan, which
is what lets the whole operation be checked before a byte is written.

The one intra-package import is a *name*: :data:`RESERVED_TARGETS` takes the
record's destination from the module that defines it. A name is not a
capability — nothing here reads or writes the record.

Substitution uses :class:`string.Template`, deliberately. It performs name
substitution and nothing else — no expressions, no conditionals, no evaluation —
which is exactly the contract the template specs require. Its
``get_identifiers()`` is how a set's placeholders are enumerated without
rendering.
"""

import keyword
import re
from collections import Counter
from string import Template

from ..core.identity import validate_segment
from .errors import (
    IncompleteTemplateSetError,
    PathConflictError,
    PathEscapeError,
    ReservedTargetError,
    UndeclaredValueError,
    UnrecognizedReferenceError,
    UnsatisfiedValueError,
)
from .plan import (
    GenerationPlan,
    PlannedFile,
    Reference,
    ReferenceKind,
    TemplateSet,
    Values,
)
from .provenance import RECORD_NAME

#: Names that must never appear in a path segment the user supplies. Traversal
#: is rejected here, in the pure layer, so it cannot depend on a filesystem
#: check that a symlink could defeat.
_UNSAFE_FRAGMENTS = ("..", "/", "\\", ":")

#: Destinations the generating operation writes itself, so no template set may
#: declare one. Sourced from the module that owns each — a reserved name has one
#: definition, and the reader of the record is what defines it.
RESERVED_TARGETS = frozenset({RECORD_NAME})

#: The values bound once per kind while rendering a ``per_kind`` template. They
#: are declared substitution values like any other, but they are supplied by the
#: repetition rather than by the caller — so validation counts them as satisfied.
#: ``kind`` is the kind's own name; ``decorator`` is the variable the generated
#: framework binds its decorator to (see :func:`decorator_names`).
PER_KIND_VALUE = "kind"
PER_KIND_DECORATOR = "decorator"
PER_KIND_VALUES = frozenset({PER_KIND_VALUE, PER_KIND_DECORATOR})


#: Schemes that designate content which must be retrieved. ``gh`` is a shorthand
#: that an adapter expands into a location; the grammar only has to know it names
#: something remote. Anything else spelled with a scheme is refused rather than
#: guessed at, so a typo never falls through to being treated as a path.
REMOTE_SCHEMES = ("gh", "https", "http", "git+https", "git+http", "git+ssh")

#: Stated back to the caller when a reference matches no form. This is the whole
#: grammar, in one place, so the error and the parser can never drift apart.
RECOGNIZED_FORMS = (
    "a set name, e.g. 'default'",
    "a directory path, e.g. './mytemplates' or 'C:\\\\templates'",
    "gh:owner/repo[@revision][#subdirectory=path]",
    "https://host/path/to/archive.tar.gz[#subdirectory=path]",
    "git+https://host/owner/repo[@revision][#subdirectory=path]",
)

#: A scheme per RFC 3986: a letter, then letters, digits, and ``+ - .``.
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")

#: A drive-qualified Windows path. Checked *before* the scheme, because
#: ``C:\templates`` satisfies the scheme grammar too and losing that race would
#: make every absolute Windows path an unrecognized scheme.
_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")

#: The fragment parameter PEP 508 uses to name a path inside retrieved content.
_SUBDIRECTORY = "subdirectory="


def parse_reference(reference: str) -> Reference:
    """
    Parse a template set reference into the form it designates.

    Total and pure: every input either yields a :class:`Reference` or raises.
    Nothing here consults a filesystem or a network, so what a reference *means*
    never depends on what happens to exist — which is what stops a mistyped
    scheme from being reported as a missing directory.

    The grammar is pip's direct-reference shape (PEP 508): ``@revision`` pins,
    ``#subdirectory=`` names a path within the content.

    Raises:
        UnrecognizedReferenceError: The reference matches no known form.
    """
    raw = reference.strip()
    if not raw:
        raise UnrecognizedReferenceError(reference, "it is empty", RECOGNIZED_FORMS)

    # A drive letter is a path, not a scheme. This ordering is the whole reason
    # the check exists; see _DRIVE.
    if _DRIVE.match(raw):
        return Reference(kind=ReferenceKind.PATH, raw=raw, scheme="", location=raw)

    matched = _SCHEME.match(raw)
    if matched:
        scheme = matched.group(1).lower()
        rest = raw[matched.end() :]
        if scheme not in REMOTE_SCHEMES:
            raise UnrecognizedReferenceError(
                raw, f"{scheme!r} is not a recognized scheme", RECOGNIZED_FORMS
            )
        # A scheme with nothing after it named no location at all.
        body, subdirectory = _split_fragment(rest)
        body, revision = _split_revision(body)
        if not body.strip("/"):
            raise UnrecognizedReferenceError(
                raw, f"the {scheme!r} scheme names no location", RECOGNIZED_FORMS
            )
        return Reference(
            kind=ReferenceKind.REMOTE,
            raw=raw,
            scheme=scheme,
            location=body,
            revision=revision,
            subdirectory=subdirectory,
        )

    # No scheme: a separator makes it a path, anything else is a bare name. A
    # bare name never silently resolves to a same-named local directory.
    if "/" in raw or "\\" in raw:
        return Reference(kind=ReferenceKind.PATH, raw=raw, scheme="", location=raw)

    return Reference(kind=ReferenceKind.NAME, raw=raw, scheme="", location=raw)


def _split_fragment(text: str) -> tuple[str, str | None]:
    """Split off ``#subdirectory=``, which is stripped before anything else.

    Order matters: a fragment can contain ``/`` and ``@``, so leaving it attached
    would corrupt every later split.
    """
    body, _, fragment = text.partition("#")
    if not fragment:
        return body, None
    for part in fragment.split("&"):
        if part.startswith(_SUBDIRECTORY):
            value = part[len(_SUBDIRECTORY) :].strip("/")
            return body, value or None
    return body, None


def _split_revision(text: str) -> tuple[str, str | None]:
    """Split off a trailing ``@revision``.

    Only an ``@`` after the final ``/`` counts, so the userinfo in
    ``git+ssh://git@host/owner/repo`` is not mistaken for a revision.
    """
    marker = text.rfind("@")
    if marker == -1 or marker < text.rfind("/"):
        return text, None
    revision = text[marker + 1 :]
    return text[:marker], revision or None


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
    - every placeholder must be satisfied by the binding its file will actually
      render with — the per-kind repetition supplies ``kind`` only to ``per_kind``
      files;
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
        bound = set(values) | (PER_KIND_VALUES if file.per_kind else set())
        for text in (file.content, file.target):
            for name in Template(text).get_identifiers():
                if name not in declared:
                    raise UndeclaredValueError(name, file.source)
                if name not in bound:
                    raise UnsatisfiedValueError(name)

    supplied = set(values) | PER_KIND_VALUES
    for name in template_set.values:
        if name not in supplied:
            raise UnsatisfiedValueError(name)


def _singular(kind: str) -> str:
    """The kind's name as one of it — `views` → `view`, `middleware` unchanged.

    A kind names a category (plural); the decorator marks one member of it
    (singular), so `@view` reads correctly on the thing it decorates. English
    has no total singularization rule and no library may be adopted for one —
    the scaffolder ships inside a distribution whose `dependencies = []` is an
    invariant — so this is deliberately conservative: it changes a name only in
    the two cases that are unambiguous and returns the kind untouched otherwise.
    A name it declines to change still generates working code; only the reading
    is less pretty, and the author owns the generated file.
    """
    if kind.endswith("ies") and len(kind) > 4:
        return kind[:-3] + "y"
    if len(kind) < 2 or not kind.endswith("s") or kind.endswith(("ss", "us", "is")):
        return kind
    return kind[:-1]


def decorator_names(kinds: tuple[str, ...]) -> dict[str, str]:
    """Map each declared kind to the decorator variable generated for it.

    One function, so the framework declaration and every app module derive the
    same name from the same input and cannot disagree. Two cases fall back to
    the kind's own name, because a pretty variable is worth less than a file
    that imports: a singular form that collides with another kind's, and one
    that is a Python keyword (`ifs` → `if`).
    """
    proposed = {kind: _singular(kind) for kind in kinds}
    taken = Counter(proposed.values())
    return {
        kind: kind
        if taken[name] > 1 or name in set(kinds) - {kind} or keyword.iskeyword(name)
        else name
        for kind, name in proposed.items()
    }


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
    ``kind`` bound to that kind — and ``decorator`` to the variable name the
    framework declaration binds for it — for both its content and its
    destination path. The repetition is declared by the manifest, not expressed
    inside a template — template content stays free of logic.

    Raises:
        UndeclaredValueError / UnsatisfiedValueError: via validation.
        PathEscapeError: If a rendered destination escapes the root.
    """
    validate_template_set(template_set, values)

    decorators = decorator_names(kinds)
    planned: list[PlannedFile] = []
    for file in template_set.files:
        bindings = (
            [
                {**values, PER_KIND_VALUE: kind, PER_KIND_DECORATOR: decorators[kind]}
                for kind in kinds
            ]
            if file.per_kind
            else [dict(values)]
        )
        for binding in bindings:
            path = _render(file.target, binding)
            _reject_escape(path)
            _reject_reserved(path)
            planned.append(
                PlannedFile(path=path, content=_render(file.content, binding))
            )

    return GenerationPlan(files=tuple(planned))


def _reject_escape(path: str) -> None:
    """Refuse a rendered destination that climbs out of the root.

    Every form the host platform would resolve outward is refused here, in the
    pure layer, before any filesystem call: traversal spelled with either
    separator, an absolute or root-relative path, and a drive- or UNC-qualified
    target. A template set is third-party content, so this is a trust boundary,
    not a typo check — the sink's own resolve check stays as defense in depth.
    """
    segments = path.replace("\\", "/").split("/")
    drive_qualified = len(path) >= 2 and path[1] == ":"
    if path.startswith(("/", "\\")) or drive_qualified or ".." in segments:
        raise PathEscapeError(path)


def _reject_reserved(path: str) -> None:
    """Refuse a rendered destination the operation writes itself.

    Checked on the rendered path rather than the declared target, so no spelling
    of a substitution reaches a reserved destination by a route the declaration
    did not show. Like :func:`_reject_escape` this is a trust boundary, not a
    typo check: a set able to write the origin record could describe its own
    provenance, which is the one thing the record must not allow.
    """
    if path.replace("\\", "/") in RESERVED_TARGETS:
        raise ReservedTargetError(path)


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
