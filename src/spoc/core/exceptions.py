"""
Custom exceptions for dynamic module importing system.

This module defines the exception classes used by the dynamic module importer
to provide clear error messages and categorization for different failure modes.
"""


class SpocError(Exception):
    """Base exception for all dynamic import errors."""

    def __init__(self, message: str, module_name: str | None = None) -> None:
        """
        Initialize a new DynamicImportError.

        Args:
            message: The error message.
            module_name: Name of the module that caused the error, if applicable.
        """
        self.module_name = module_name
        super().__init__(
            f"{message} {f'(module: {module_name})' if module_name else ''}"
        )


class AppNotFoundError(SpocError):
    """Raised when a module cannot be found during dynamic import."""

    def __init__(self, module_name: str) -> None:
        """
        Initialize a new ModuleNotFoundError.

        Args:
            module_name: Name of the module that could not be found.
        """
        super().__init__("Module could not be found", module_name)


class ModuleNotCachedError(SpocError):
    """Raised when attempting to access a module that is not in the cache."""

    def __init__(self, module_name: str) -> None:
        """
        Initialize a new ModuleNotCachedError.

        Args:
            module_name: Name of the module that is not cached.
        """
        super().__init__("Module is not cached", module_name)


class CircularDependencyError(SpocError):
    """Raised when a circular dependency is detected during startup/shutdown."""

    def __init__(self, modules: list[str]) -> None:
        """
        Initialize a new CircularDependencyError.

        Args:
            modules: List of modules involved in the circular dependency.
        """
        modules_str = " -> ".join(modules)
        super().__init__(f"Circular dependency detected: {modules_str}")


class MalformedIdentifierError(SpocError):
    """Raised when a string does not parse as ``kind:namespace.object_name``."""

    def __init__(self, identifier: str, reason: str) -> None:
        self.identifier = identifier
        self.reason = reason
        super().__init__(
            f"Malformed identifier {identifier!r}: {reason}. "
            "Expected kind:namespace.object_name "
            "(each segment ^[a-z][a-z0-9_]*$)"
        )


class InvalidSegmentError(SpocError):
    """
    Raised when an identifier segment violates the grammar.

    Names derived from an object are converted to snake_case first, so this
    fires only for a value that cannot conform even after conversion, or for
    a name the author stated explicitly — those are used verbatim.
    """

    def __init__(self, segment: str, value: object) -> None:
        self.segment = segment
        self.value = value
        super().__init__(
            f"Invalid {segment} segment {value!r}: "
            "must match ^[a-z][a-z0-9_]*$ (lowercase snake_case). "
            "A name passed explicitly is used verbatim — pass a conforming "
            "one, or omit it to derive the name from the object"
        )


class UnknownKindError(SpocError):
    """Raised when a kind is not in the declared (closed) kind set."""

    def __init__(self, kind: str, declared: tuple[str, ...]) -> None:
        self.kind = kind
        self.declared = declared
        super().__init__(
            f"Unknown kind {kind!r}. Declared kinds: {', '.join(declared) or '(none)'}"
        )


class UnknownNamespaceError(SpocError):
    """Raised when resolution finds no components of a kind in a namespace."""

    def __init__(self, namespace: str, kind: str, candidates: tuple[str, ...]) -> None:
        self.namespace = namespace
        self.kind = kind
        self.candidates = candidates
        super().__init__(
            f"Unknown namespace {namespace!r} for kind {kind!r}. "
            f"Namespaces with {kind!r} components: "
            f"{', '.join(candidates) or '(none)'}"
        )


class UnknownObjectError(SpocError):
    """Raised when resolution finds no object of that name in kind:namespace."""

    def __init__(
        self, name: str, kind: str, namespace: str, candidates: tuple[str, ...]
    ) -> None:
        self.name = name
        self.kind = kind
        self.namespace = namespace
        self.candidates = candidates
        super().__init__(
            f"Unknown object_name {name!r} in {kind}:{namespace}. "
            f"Registered: {', '.join(candidates) or '(none)'}"
        )


class DuplicateComponentError(SpocError):
    """Raised when a second object is registered under an existing identifier."""

    def __init__(self, identifier: str, existing: object) -> None:
        self.identifier = identifier
        self.existing = existing
        super().__init__(
            f"Duplicate identifier {identifier!r}: already registered to {existing!r}"
        )


class ComponentKindMismatchError(SpocError):
    """
    Raised when a declared component's kind does not match its location.

    Layout is taxonomy: objects in ``<app>/<kind>.py`` must declare that kind.
    A mismatch is a startup error, never a silent omission.
    """

    def __init__(
        self, obj_name: str, declared_kind: str, location_kind: str, module: str
    ) -> None:
        self.obj_name = obj_name
        self.declared_kind = declared_kind
        self.location_kind = location_kind
        super().__init__(
            f"Component {obj_name!r} declares kind {declared_kind!r} but was "
            f"discovered in module {module!r}, which holds kind {location_kind!r}. "
            "Move the declaration or fix its kind",
            module,
        )


class MissingNameError(SpocError):
    """Raised when a nameless object is registered without an explicit name."""

    def __init__(self, obj: object) -> None:
        self.obj = obj
        super().__init__(
            f"Cannot register {obj!r}: it has no __name__, so an explicit "
            "name is required — register(kind, obj, name='...'). "
            "Identity is never inferred from the execution environment"
        )


class ConfigurationError(SpocError):
    """Error in configuration loading or validation."""

    def __init__(
        self,
        message: str,
        config_file: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize a ConfigurationError.

        Args:
            message: Error message
            config_file: The configuration file that caused the error
            original_error: The original exception that caused this error
        """
        self.config_file = config_file
        error_msg = message
        if config_file:
            error_msg = f"{message} in file {config_file}"

        # Store the original error separately, don't pass it to SpocError
        self.original_error = original_error
        super().__init__(error_msg, None)
