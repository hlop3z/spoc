"""
Project scaffolding for spoc — the ``spoc init`` surface.

Used once, at the beginning of a project: it emits a configuration file, a
framework declaration, one app, and an entry point that starts unedited. That
generated app is also the worked example for adding the second one by hand.

The kernel does not import anything from here. The dependency runs one way, so
this package can be deleted without touching the kernel — and nothing in it
requires a dependency the kernel does not already have.
"""

from .errors import (
    IncompleteTemplateSetError,
    PathConflictError,
    PathEscapeError,
    ScaffoldError,
    TargetNotEmptyError,
    TemplateSetNotFoundError,
    UndeclaredValueError,
    UnsatisfiedValueError,
)
from .operations import DEFAULT_APP_NAME, DEFAULT_KINDS, init_project
from .plan import (
    GenerationPlan,
    PlannedFile,
    ProjectSink,
    TemplateFile,
    TemplateSet,
    TemplateSource,
)
from .sink import DirectorySink
from .sources import ENTRY_POINT_GROUP, InstalledTemplateSources

__all__ = [
    # Operation
    "init_project",
    "DEFAULT_KINDS",
    "DEFAULT_APP_NAME",
    # Plan and ports
    "GenerationPlan",
    "PlannedFile",
    "TemplateFile",
    "TemplateSet",
    "TemplateSource",
    "ProjectSink",
    # Adapters
    "DirectorySink",
    "InstalledTemplateSources",
    "ENTRY_POINT_GROUP",
    # Errors
    "ScaffoldError",
    "TargetNotEmptyError",
    "PathConflictError",
    "PathEscapeError",
    "TemplateSetNotFoundError",
    "IncompleteTemplateSetError",
    "UnsatisfiedValueError",
    "UndeclaredValueError",
]
