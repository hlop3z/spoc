"""
The kernel's error family.

Every failure the kernel can produce is one of these, and each carries its facts as
attributes as well as in its message — so a caller can catch a specific class and read
what failed without parsing text.

Two properties are contractual, not stylistic. Resolution fails **per segment**, in the
order kind → namespace → object_name, and each error names the failing segment, the value
it received, and the candidates that were valid at that step. Discovery is **loud**: a
declared component that cannot be registered raises rather than being dropped. The
messages below are the user-visible surface of both promises.
"""

from __future__ import annotations


class SpocError(Exception):
    """Base for every kernel error."""

    def __init__(self, message: str, module_name: str | None = None) -> None:
        self.module_name = module_name
        suffix = f" (module: {module_name})" if module_name else " "
        super().__init__(f"{message}{suffix}")


class AppNotFoundError(SpocError):
    """A module could not be imported."""

    def __init__(self, module_name: str) -> None:
        super().__init__("Module could not be found", module_name)


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
    """An identifier segment violates the grammar."""

    def __init__(self, segment: str, value: object) -> None:
        self.segment, self.value = segment, value
        super().__init__(
            f"Invalid {segment} segment {value!r}: "
            "must match ^[a-z][a-z0-9_]*$ (lowercase snake_case). "
            "A name passed explicitly is used verbatim — pass a conforming "
            "one, or omit it to derive the name from the object"
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
        self, name: str, kind: str, namespace: str, candidates: tuple[str, ...]
    ) -> None:
        self.name, self.kind, self.namespace = name, kind, namespace
        self.candidates = candidates
        super().__init__(
            f"Unknown object_name {name!r} in {kind}:{namespace}. "
            f"Registered: {', '.join(candidates) or '(none)'}"
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
            "name is required — register(kind, obj, name='...'). "
            "Identity is never inferred from the execution environment"
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
