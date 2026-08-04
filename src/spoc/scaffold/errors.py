"""
Failures the scaffolder can raise.

Every one of these is a *refusal before writing*: the scaffolder computes and
validates a whole plan first, so a raised error means nothing reached disk.
Each names the offending value, because a scaffolder that fails without saying
which path collided is worse than one that never ran.
"""

from ..core.exceptions import SpocError


class ScaffoldError(SpocError):
    """Base for every scaffolding failure."""


class TargetNotEmptyError(ScaffoldError):
    """Raised when the destination directory already contains content."""

    def __init__(self, target: str) -> None:
        self.target = target
        super().__init__(
            f"Target directory is not empty: {target}. "
            "Generation refuses to write into a directory it did not create"
        )


class PathConflictError(ScaffoldError):
    """Raised when a planned path already exists at the destination."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(
            f"Refusing to overwrite existing path: {path}. Nothing was written"
        )


class PathEscapeError(ScaffoldError):
    """Raised when a supplied name would resolve outside the target."""

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(
            f"Refusing to write outside the target directory: {value!r} "
            "resolves beyond the destination root"
        )


class TemplateSetNotFoundError(ScaffoldError):
    """Raised when a named template set cannot be resolved."""

    def __init__(self, reference: str, candidates: tuple[str, ...]) -> None:
        self.reference = reference
        self.candidates = candidates
        listed = ", ".join(candidates) if candidates else "none installed"
        super().__init__(f"Unknown template set: {reference!r}. Available: {listed}")


class IncompleteTemplateSetError(ScaffoldError):
    """Raised when a template set omits something the operation requires."""

    def __init__(self, missing: str) -> None:
        self.missing = missing
        super().__init__(
            f"Template set is incomplete: missing {missing}. Nothing was written"
        )


class UnsatisfiedValueError(ScaffoldError):
    """Raised when a template needs a substitution value nobody supplied."""

    def __init__(self, value_name: str) -> None:
        self.value_name = value_name
        super().__init__(
            f"Template set requires the substitution value {value_name!r}, "
            "which this operation does not supply. Nothing was written"
        )


class UndeclaredValueError(ScaffoldError):
    """Raised when a template uses a placeholder the manifest never declared."""

    def __init__(self, value_name: str, source: str) -> None:
        self.value_name = value_name
        self.source = source
        super().__init__(
            f"Template {source} uses the placeholder {value_name!r}, which the "
            "manifest does not declare. Substitution values must be enumerable "
            "without rendering"
        )
