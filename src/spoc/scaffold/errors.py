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
    """Raised when a named template set cannot be resolved.

    Candidates come only from sources that can actually enumerate themselves, so
    this never presents an invented list as the set of possibilities.
    """

    def __init__(self, reference: str, candidates: tuple[str, ...]) -> None:
        self.reference = reference
        self.candidates = candidates
        listed = ", ".join(candidates) if candidates else "none installed"
        super().__init__(f"Unknown template set: {reference!r}. Available: {listed}")


class UnrecognizedReferenceError(ScaffoldError):
    """Raised when a reference matches no known form.

    Distinct from :class:`TemplateSetNotFoundError` on purpose: that one means
    "this named a form I understand, and it was not there", this one means "I do
    not know what you asked for". Reporting the second as the first is how a
    mistyped scheme ends up complaining about a missing directory nobody named.
    """

    def __init__(self, reference: str, segment: str, forms: tuple[str, ...]) -> None:
        self.reference = reference
        self.segment = segment
        self.forms = forms
        listed = "\n  ".join(forms)
        super().__init__(
            f"Unrecognized template reference: {reference!r} — {segment}. "
            f"Recognized forms:\n  {listed}\nNothing was written"
        )


class RetrievalError(ScaffoldError):
    """Raised when a remote reference cannot be retrieved."""

    def __init__(self, reference: str, reason: str) -> None:
        self.reference = reference
        self.reason = reason
        super().__init__(
            f"Could not retrieve template set {reference!r}: {reason}. Nothing was written"
        )


class InsecureRedirectError(ScaffoldError):
    """Raised when retrieval is redirected onto weaker guarantees than were asked for."""

    def __init__(self, origin: str, destination: str) -> None:
        self.origin = origin
        self.destination = destination
        super().__init__(
            f"Refusing redirect from {origin!r} to {destination!r}: the destination "
            "offers weaker guarantees than the reference supplied. Nothing was written"
        )


class MemberRefusedError(ScaffoldError):
    """Raised when retrieved content carries a member that may not be materialized.

    This is the trust boundary for third-party archives. It fires for traversal,
    absolute paths, links, and special files — and it fires again, independently,
    after a member is materialized, because the standard library's own extraction
    filter has had a traversal bypass (CVE-2025-4517) on interpreter versions this
    project supports.
    """

    def __init__(self, member: str, reason: str) -> None:
        self.member = member
        self.reason = reason
        super().__init__(
            f"Refusing archive member {member!r}: {reason}. Nothing was written"
        )


class BoundExceededError(ScaffoldError):
    """Raised when retrieved content exceeds a declared bound."""

    def __init__(self, bound_name: str, limit: int) -> None:
        self.bound_name = bound_name
        self.limit = limit
        super().__init__(
            f"Retrieved content exceeds the {bound_name} bound of {limit}. "
            "Nothing was written"
        )


class RevisionUnavailableError(ScaffoldError):
    """Raised when a revision is neither retained nor retrievable."""

    def __init__(self, reference: str, reason: str) -> None:
        self.reference = reference
        self.reason = reason
        super().__init__(
            f"Template set {reference!r} is not retained locally and could not be "
            f"retrieved ({reason}). Nothing was written"
        )


class IncompleteTemplateSetError(ScaffoldError):
    """Raised when a template set omits something the operation requires."""

    def __init__(self, missing: str) -> None:
        self.missing = missing
        super().__init__(
            f"Template set is incomplete: missing {missing}. Nothing was written"
        )


class ReservedTargetError(ScaffoldError):
    """Raised when a template set declares a file the operation writes itself.

    What a set may declare is bounded in both directions: it must supply
    everything the operation requires, and it may not claim anything the
    operation reserves. A set that could write the origin record could describe
    its own provenance — which is worth refusing loudly rather than ignoring.
    """

    def __init__(self, target: str) -> None:
        self.target = target
        super().__init__(
            f"Template set declares {target!r}, which is reserved: the scaffolder "
            "writes it itself, for every generation. Remove it from the manifest. "
            "Nothing was written"
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
