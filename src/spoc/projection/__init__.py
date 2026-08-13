"""
The registry, projected as data.

``kind:namespace.object_name`` is the most durable thing this project owns: a
naming standard, not a Python API, implementable and queryable by systems that
never import ``spoc``. This subpackage is what makes it portable — one document
describing what a project registered, validated by a published JSON Schema, so
a router generator, an admin surface, a documentation build, or a client in
another language can read a registry without parsing Python.

The document describes the registry **as of the completion of discovery**. Ready
callbacks run inside discovery and are therefore included; anything a startup
hook registers afterwards is not, and a consumer must not read the projection as
a claim about a fully started process.

Nothing in the kernel imports this package. Like ``scaffold``, ``stubs``, and
``formats``, it is reached through the CLI or as a library call and depends
inward only — but unlike them it is also depended *on*: :mod:`spoc.stubs` builds
its manifest from a projection, so the stub and the document cannot disagree
about what a project registered.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from .cli import register
from .document import (
    FORMAT_VERSION,
    ComponentEntry,
    Projection,
    dumps,
)
from .produce import project

#: The consumer surface, and deliberately only that. ``collected`` and
#: ``projection_of`` in :mod:`spoc.projection.produce` are the seam the stub
#: generator reuses to avoid owning a second collect-only boot; they stay
#: exposed from a plain module, which under the stability contract is what
#: makes them internal. Splitting a boot in half is not a promise worth making.
__all__ = [
    "FORMAT_VERSION",
    "SCHEMA_FILENAME",
    "ComponentEntry",
    "Projection",
    "dumps",
    "project",
    # Mounting the command under a downstream framework's own command name. The
    # mount is promised weakly and the document it writes strongly — a consumer
    # reading the projection depends on the schema, not on how the command that
    # produced it was reached.
    "register",
    "schema_path",
    "schema_text",
]

#: The published schema, shipped beside this module so that obtaining it never
#: requires network access or a matching release on disk elsewhere.
SCHEMA_FILENAME = "schema.json"


def schema_path() -> Path:
    """The filesystem path of the published JSON Schema.

    Consumers outside Python are expected to fetch the file from the project's
    repository; this exists so that anything already running in this process —
    the test suite, a documentation build, a validating consumer — reads the
    same bytes rather than a copy that could drift.
    """
    return Path(str(files(__package__) / SCHEMA_FILENAME))


def schema_text() -> str:
    """The published JSON Schema, as text."""
    return schema_path().read_text(encoding="utf-8")
