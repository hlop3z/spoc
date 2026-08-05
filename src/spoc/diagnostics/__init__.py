"""
Project diagnostics — a contained subpackage.

Pre-runtime validation (`check`) and read-only registry introspection
(`list_records`, `explain`) as library-first operations; the ``spoc`` CLI
mounts them as thin subcommand adapters. The kernel never imports this;
importing :mod:`spoc` never loads it.

A diagnostic run is an isolated dry boot: the operations compose
:mod:`spoc.testing`'s isolation scopes, so no framework state, loaded app
modules, or import-path changes outlive a call.
"""

from .core import CheckReport, Finding, RecordInfo, check, explain, list_records
from .locate import DEFAULT_FRAMEWORK_REF, LocateError

__all__ = [
    # Operations
    "check",
    "list_records",
    "explain",
    # Results
    "CheckReport",
    "Finding",
    "RecordInfo",
    # Location
    "DEFAULT_FRAMEWORK_REF",
    "LocateError",
]
