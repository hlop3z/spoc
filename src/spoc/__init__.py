"""
SPOC — a component registry and lifecycle for modular monolithic applications.

Declare a framework once — its kinds and their attributes — on one ``Framework`` object,
then ``start(base_dir)``. SPOC discovers apps, loads their modules in dependency order,
manages lifecycle, and registers every declared object in one flat registry under a
canonical identifier: ``kind:namespace.object_name``. External surfaces (HTTP, CLI,
workers) are built on top by enumerating the registry — SPOC describes, it never
executes.

What follows is the whole public surface. ``spoc.core`` is **internal** — it holds the
declaration layer, the module loader, and the configuration adapter, and nothing in it
carries a stability promise, however reachable it happens to be. Anything a framework
author legitimately needs is re-exported here; if something you need is only reachable
under ``spoc.core``, that is a gap to report, not an API to import.

Tiers for every name below are declared in ``[tool.spoc.stability]`` in ``pyproject.toml``
and enforced by ``apicheck``. See the stability policy in the docs.
"""

import logging

from .__about__ import __version__
from .core.declaration import KindHandle, KindSpec, component
from .core.exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    ComponentKindMismatchError,
    ComponentShapeError,
    ConfigurationError,
    DuplicateComponentError,
    FrameworkTransitioningError,
    IdentityDivergenceError,
    InvalidSegmentError,
    MalformedIdentifierError,
    MetadataContractError,
    MissingModuleError,
    MissingNameError,
    SpocError,
    UnknownKindError,
    UnknownNamespaceError,
    UnknownObjectError,
    UnmarkableObjectError,
    UnresolvedReferenceError,
)
from .core.identity import Identifier, compose, parse
from .core.registry import Component, Registry
from .framework import Config, Framework

# A library configures nothing and prints nothing. Without this, Python's
# `lastResort` handler writes WARNING and above straight to stderr, so an
# application that never configured logging would see SPOC's records unbidden.
#
# `spoc` is the stable handle to configure: attach a handler or set a level on
# it to receive them. Names *below* it follow module paths (`spoc.framework`,
# `spoc.core.loader`) for per-subsystem control, and are internal — relocating
# a module is not a breaking change to anyone's logging configuration.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    # Package
    "__version__",
    # Declaration
    "Framework",
    "KindSpec",
    "KindHandle",
    "Config",
    "component",
    # Registry
    "Registry",
    "Component",
    # Identity
    "Identifier",
    "parse",
    "compose",
    # Exceptions
    "SpocError",
    "AppNotFoundError",
    "MissingModuleError",
    "CircularDependencyError",
    "ConfigurationError",
    "MalformedIdentifierError",
    "InvalidSegmentError",
    "UnknownKindError",
    "UnknownNamespaceError",
    "UnknownObjectError",
    "FrameworkTransitioningError",
    "UnresolvedReferenceError",
    "DuplicateComponentError",
    "IdentityDivergenceError",
    "ComponentKindMismatchError",
    "ComponentShapeError",
    "MissingNameError",
    "UnmarkableObjectError",
    "MetadataContractError",
]
