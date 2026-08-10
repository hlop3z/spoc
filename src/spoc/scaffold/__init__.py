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

**What this namespace publishes.** A name appears below only because a consumer
outside this package must write it to do something the package offers: invoke an
operation, implement a contract it accepts, distinguish a failure it can respond
to differently, or supply a value it reads. Everything else — the retrieval
ports and their adapters, archive admission, the record-writing half of
provenance, and the error leaves that admit no distinct response — is this
package assembling itself, and stays in its defining submodule.

Those submodules remain importable, and importing from one is a normal thing to
do. It carries no stability promise: reaching an internal element is not a
promotion. What changed is what is promised, not what is reachable.
"""

from ..core.deprecation import deprecated_alias
from . import archive
from .errors import (
    RetrievalError,
    ScaffoldError,
    TargetNotEmptyError,
    TemplateSetNotFoundError,
    UnrecognizedReferenceError,
)
from .operations import (
    DEFAULT_APP_NAME,
    DEFAULT_KINDS,
    AddedApp,
    add_app,
    init_project,
)
from .plan import (
    EnumerableSource,
    GenerationPlan,
    PlannedFile,
    ProjectSink,
    TemplateFile,
    TemplateSet,
    TemplateSource,
)
from .provenance import RECORD_NAME, Origin, read_origin
from .sink import DirectorySink
from .sources import ENTRY_POINT_GROUP, InstalledTemplateSources

#: Archive admission is how retrieval is made safe, not something a consumer
#: composes with — it belongs to the module that performs it. The name stays
#: here, warning, for one minor release so the migration is discoverable by
#: running the code rather than by reading a changelog.
extract_archive = deprecated_alias(
    archive.extract_archive,
    "spoc.scaffold.extract_archive is deprecated; import it from "
    "spoc.scaffold.archive instead. The re-export is removed at 1.0.",
)

__all__ = [
    # Operations
    "init_project",
    "add_app",
    "AddedApp",
    "DEFAULT_KINDS",
    "DEFAULT_APP_NAME",
    # Plan, and the ports the operations take
    "GenerationPlan",
    "PlannedFile",
    "TemplateFile",
    "TemplateSet",
    "TemplateSource",
    "EnumerableSource",
    "ProjectSink",
    # The adapters that satisfy those ports without writing one
    "DirectorySink",
    "InstalledTemplateSources",
    "ENTRY_POINT_GROUP",
    # Reading a project's origin
    "Origin",
    "read_origin",
    "RECORD_NAME",
    # Archive admission — deprecated here, see spoc.scaffold.archive
    "extract_archive",
    # Errors: the category, and the four that admit a distinct response
    "ScaffoldError",
    "TargetNotEmptyError",
    "TemplateSetNotFoundError",
    "UnrecognizedReferenceError",
    "RetrievalError",
]
