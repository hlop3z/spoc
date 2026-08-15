"""
Project diagnostics — a contained subpackage.

Pre-runtime validation (`check`) and read-only registry introspection
(`list_records`, `explain`) as library-first operations; the ``spoc`` CLI
mounts them as thin subcommand adapters. The kernel never imports this;
importing :mod:`spoc` never loads it.

A diagnostic run is an isolated dry boot: the operations compose
:mod:`spoc.testing`'s isolation scopes, so no framework state, loaded app
modules, or import-path changes outlive a call.

Records are described by :class:`spoc.projection.ComponentEntry` rather than by
a structure of this subpackage's own. One registry has one description; what
differs between `spoc list` and `spoc projection` is the boot depth and the
rendering, which is the whole of the difference.
"""

from ..locate import DEFAULT_FRAMEWORK_REF, LocateError
from ..projection import ComponentEntry
from .cli import register
from .core import (
    CHECK_FORMAT_VERSION,
    CheckReport,
    Finding,
    check,
    explain,
    list_records,
)

__all__ = [
    # Operations
    "check",
    "list_records",
    "explain",
    # Results
    "CHECK_FORMAT_VERSION",
    "CheckReport",
    "ComponentEntry",
    "Finding",
    # Location
    "DEFAULT_FRAMEWORK_REF",
    "LocateError",
    # Mounting validation and introspection under a downstream framework's own
    # command name — the inspection half of the same path the generation line
    # publishes.
    "register",
]
