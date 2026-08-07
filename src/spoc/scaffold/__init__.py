"""
Project scaffolding for spoc — the ``spoc init`` and ``spoc app`` surfaces.

Used once, at the beginning of a project: it emits a configuration file, a
framework declaration, one app, an entry point that starts unedited, and a
record of the template set it all came from. That generated app is also the
worked example for adding the second one by hand.

A template set may be built in, installed by a downstream distribution, read
from a directory, or retrieved from a remote location — the reference's own
spelling decides which, before anything is looked up. Retrieved content is
admitted rather than trusted, and everything after admission is identical to a
local set: origin buys no capability.

The kernel does not import anything from here. The dependency runs one way, so
this package can be deleted without touching the kernel — and nothing in it
requires a dependency the kernel does not already have, retrieval included.
"""

from .archive import MAX_EXPANDED_BYTES, MAX_MEMBERS, extract_archive
from .cache import DirectoryCache, default_cache_root
from .errors import (
    BoundExceededError,
    IncompleteTemplateSetError,
    InsecureRedirectError,
    MemberRefusedError,
    PathConflictError,
    PathEscapeError,
    ReservedTargetError,
    RetrievalError,
    RevisionUnavailableError,
    ScaffoldError,
    TargetNotEmptyError,
    TemplateSetNotFoundError,
    UndeclaredValueError,
    UnrecognizedReferenceError,
    UnsatisfiedValueError,
)
from .operations import (
    DEFAULT_APP_NAME,
    DEFAULT_KINDS,
    AddedApp,
    add_app,
    init_project,
)
from .plan import (
    Cache,
    EnumerableSource,
    Fetcher,
    GenerationPlan,
    PlannedFile,
    ProjectSink,
    Reference,
    ReferenceKind,
    RevisionResolver,
    TemplateFile,
    TemplateSet,
    TemplateSource,
)
from .provenance import (
    RECORD_NAME,
    Origin,
    describe_divergence,
    read_origin,
    record_content,
    record_file,
)
from .remote import HttpFetcher, HttpRevisionResolver
from .sink import DirectorySink
from .sources import ENTRY_POINT_GROUP, InstalledTemplateSources, RemoteTemplateSource

__all__ = [
    # Operations
    "init_project",
    "add_app",
    "AddedApp",
    "DEFAULT_KINDS",
    "DEFAULT_APP_NAME",
    # Plan and ports
    "GenerationPlan",
    "PlannedFile",
    "TemplateFile",
    "TemplateSet",
    "Reference",
    "ReferenceKind",
    "TemplateSource",
    "EnumerableSource",
    "ProjectSink",
    "RevisionResolver",
    "Fetcher",
    "Cache",
    # Adapters
    "DirectorySink",
    "InstalledTemplateSources",
    "RemoteTemplateSource",
    "HttpRevisionResolver",
    "HttpFetcher",
    "DirectoryCache",
    "default_cache_root",
    "ENTRY_POINT_GROUP",
    # Archive admission
    "extract_archive",
    "MAX_EXPANDED_BYTES",
    "MAX_MEMBERS",
    # Provenance
    "Origin",
    "record_content",
    "record_file",
    "read_origin",
    "describe_divergence",
    "RECORD_NAME",
    # Errors
    "ScaffoldError",
    "TargetNotEmptyError",
    "PathConflictError",
    "PathEscapeError",
    "TemplateSetNotFoundError",
    "UnrecognizedReferenceError",
    "IncompleteTemplateSetError",
    "UnsatisfiedValueError",
    "UndeclaredValueError",
    "ReservedTargetError",
    "RetrievalError",
    "InsecureRedirectError",
    "MemberRefusedError",
    "BoundExceededError",
    "RevisionUnavailableError",
]
