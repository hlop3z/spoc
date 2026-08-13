"""
The kernel's error family.

Every failure the kernel itself produces is one of these, and each carries its facts as
attributes as well as in its message — so a caller can catch a specific class and read
what failed without parsing text. Failures authored by app code are not the kernel's: a
module that raises while importing propagates its own exception, because the author
needs their traceback, not a wrapper around it.

Three properties are contractual, not stylistic. Resolution fails **per segment**, in the
order kind → namespace → object_name, and each error names the failing segment, the value
it received, and the candidates that were valid at that step. A segment failure **means the
segment**: a read refused because a lifecycle transition is in flight is its own error, so
"unknown namespace" is never how the kernel reports its own timing. Discovery is **loud**: a
declared component that cannot be registered raises rather than being dropped. The
messages below are the user-visible surface of all three promises.
"""

from __future__ import annotations


class SpocError(Exception):
    """Base for every kernel error."""

    def __init__(self, message: str, module_name: str | None = None) -> None:
        self.module_name = module_name
        suffix = f" (module: {module_name})" if module_name else ""
        super().__init__(f"{message}{suffix}")


class AppNotFoundError(SpocError):
    """A module could not be imported."""

    def __init__(self, module_name: str) -> None:
        super().__init__("Module could not be found", module_name)


class UnresolvedReferenceError(SpocError):
    """A ``package.module.attribute`` reference names something that does not exist."""

    def __init__(self, uri: str, reason: str) -> None:
        self.uri, self.reason = uri, reason
        super().__init__(f"Cannot resolve reference {uri!r}: {reason}")


class MissingModuleError(SpocError):
    """An app provides no module for a kind whose modules are required."""

    def __init__(self, app: str, kind: str, module: str) -> None:
        self.app, self.kind = app, kind
        super().__init__(
            f"App {app!r} provides no {kind!r} module. Expected {module!r}. "
            f"Declare the kind as optional if apps may omit it",
            module,
        )


class CircularDependencyError(SpocError):
    """Module dependencies form a cycle."""

    def __init__(self, modules: list[str]) -> None:
        self.modules = modules
        super().__init__(f"Circular dependency detected: {' -> '.join(modules)}")


class MalformedIdentifierError(SpocError):
    """A string does not parse as ``kind:namespace.object_name``."""

    def __init__(self, identifier: str, reason: str) -> None:
        self.identifier, self.reason = identifier, reason
        super().__init__(
            f"Malformed identifier {identifier!r}: {reason}. "
            "Expected kind:namespace.object_name "
            "(each segment ^[a-z][a-z0-9_]*$)"
        )


class InvalidSegmentError(SpocError):
    """An identifier segment violates the grammar.

    The remediation describes the path the name actually took: `derived_from`
    names the intrinsic name the value was converted from, and is None when the
    caller stated the value outright.
    """

    def __init__(
        self, segment: str, value: object, *, derived_from: str | None = None
    ) -> None:
        self.segment, self.value = segment, value
        self.derived_from = derived_from
        if derived_from is None:
            remedy = (
                "A name passed explicitly is used verbatim — pass a conforming "
                "one, or omit it to derive the name from the object"
            )
        else:
            remedy = (
                f"This name was derived from {derived_from!r} and still does not "
                "conform — pass a conforming name explicitly, or rename the object"
            )
        super().__init__(
            f"Invalid {segment} segment {value!r}: "
            f"must match ^[a-z][a-z0-9_]*$ (lowercase snake_case). {remedy}"
        )


class UnknownKindError(SpocError):
    """A kind is not in the declared (closed) kind set."""

    def __init__(self, kind: str, declared: tuple[str, ...]) -> None:
        self.kind, self.declared = kind, declared
        super().__init__(
            f"Unknown kind {kind!r}. Declared kinds: {', '.join(declared) or '(none)'}"
        )


class UnknownNamespaceError(SpocError):
    """Resolution found no components of a kind in a namespace."""

    def __init__(self, namespace: str, kind: str, candidates: tuple[str, ...]) -> None:
        self.namespace, self.kind, self.candidates = namespace, kind, candidates
        super().__init__(
            f"Unknown namespace {namespace!r} for kind {kind!r}. "
            f"Namespaces with {kind!r} components: "
            f"{', '.join(candidates) or '(none)'}"
        )


class UnknownObjectError(SpocError):
    """Resolution found no object of that name in kind:namespace."""

    def __init__(
        self, object_name: str, kind: str, namespace: str, candidates: tuple[str, ...]
    ) -> None:
        self.object_name, self.kind, self.namespace = object_name, kind, namespace
        self.candidates = candidates
        super().__init__(
            f"Unknown object_name {object_name!r} in {kind}:{namespace}. "
            f"Registered: {', '.join(candidates) or '(none)'}"
        )


class FrameworkTransitioningError(SpocError):
    """A read arrived from outside an in-flight lifecycle transition.

    The identifier is not the problem; the timing is. This is deliberately not
    one of the unknown-segment errors above: during a transition the registry is
    half-built or already replaced, so answering "unknown namespace" would report
    a typo the caller did not make, and answering successfully would hand back a
    component whose teardown has already run.

    `transition` names the phase in flight — the same word the caller invoked —
    so the remedy points at a specific call rather than at lifecycle in general.
    """

    def __init__(self, identifier: str, transition: str) -> None:
        self.identifier, self.transition = identifier, transition
        super().__init__(
            f"Cannot resolve {identifier!r} while the framework is inside "
            f"{transition}: this call is not part of that transition, and a "
            "component reached "
            "during one may already have been torn down. Order the read against "
            "the transition — a served application usually gets that ordering "
            "from its server, which finishes in-flight work before shutting the "
            "application down"
        )


class IdentityDivergenceError(SpocError):
    """An already-registered object was re-registered under a different identity."""

    def __init__(self, existing_identifier: str, requested_identifier: str) -> None:
        self.existing_identifier = existing_identifier
        self.requested_identifier = requested_identifier
        super().__init__(
            f"Object already registered as {existing_identifier!r}; refusing to "
            f"register it again as {requested_identifier!r}. One object holds "
            "exactly one canonical identifier"
        )


class DuplicateComponentError(SpocError):
    """A second object was registered under an existing identifier."""

    def __init__(self, identifier: str, existing: object) -> None:
        self.identifier, self.existing = identifier, existing
        super().__init__(
            f"Duplicate identifier {identifier!r}: already registered to {existing!r}"
        )


class ComponentKindMismatchError(SpocError):
    """A declared component's kind does not match its location — layout is taxonomy."""

    def __init__(
        self, obj_name: str, declared_kind: str, location_kind: str, module: str
    ) -> None:
        self.obj_name = obj_name
        self.declared_kind, self.location_kind = declared_kind, location_kind
        super().__init__(
            f"Component {obj_name!r} declares kind {declared_kind!r} but was "
            f"discovered in module {module!r}, which holds kind {location_kind!r}. "
            "Move the declaration or fix its kind",
            module,
        )


class MissingNameError(SpocError):
    """A nameless object was registered without an explicit name."""

    def __init__(self, obj: object) -> None:
        self.obj = obj
        super().__init__(
            f"Cannot register {obj!r}: it has no __name__, so an explicit "
            "name is required — pass name='...' to the kind decorator. "
            "Identity is never inferred from the execution environment"
        )


class UnmarkableObjectError(SpocError):
    """An object cannot carry the declaration marker."""

    def __init__(self, obj: object, reason: str) -> None:
        self.obj, self.reason = obj, reason
        super().__init__(
            f"Cannot mark {obj!r} as a component: it does not accept the "
            f"'__spoc__' attribute ({reason}). Objects restricting their "
            "attributes — __slots__ without '__spoc__', or a built-in type — "
            "cannot be marked; wrap the value or register it as a plugin"
        )


class MetadataContractError(SpocError):
    """Component metadata departs from the contract its kind declares."""

    def __init__(
        self, kind: str, obj_name: str, expected: type | None, got: object
    ) -> None:
        self.kind, self.obj_name, self.expected, self.got = (
            kind,
            obj_name,
            expected,
            got,
        )
        if expected is None:
            detail = (
                f"kind {kind!r} declares no metadata contract, so its components "
                f"carry no metadata — got {type(got).__name__}"
            )
        else:
            detail = (
                f"kind {kind!r} declares metadata {expected.__name__}, "
                f"got {type(got).__name__}"
            )
        super().__init__(f"Component {obj_name!r} metadata does not conform: {detail}")


class ConfigurationError(SpocError):
    """Configuration could not be loaded or failed validation."""

    def __init__(self, message: str, config_file: str | None = None) -> None:
        self.config_file = config_file
        super().__init__(f"{message} in file {config_file}" if config_file else message)


class ComponentShapeError(SpocError):
    """A component's shape is not the shape the caller's type contract expects.

    Shape is the one thing typed access checks at runtime — whether the record
    holds something constructible, a plain value, or a callable. Structure is
    not checked here: which members an object provides is a static question,
    and answering it twice would put a validation engine in the kernel.
    """

    def __init__(self, identifier: str, expected: str, got: str) -> None:
        self.identifier, self.expected, self.got = identifier, expected, got
        super().__init__(
            f"Component {identifier!r} is {got}, but the requested access "
            f"expects {expected}. Use the accessor matching the component's "
            "shape, or register a different object under this identifier"
        )
