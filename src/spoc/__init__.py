"""
SPOC — a registry-first runtime kernel for modular monolithic applications.

Declare a framework once — its kinds and their attributes — on one ``Framework`` object,
then ``start(base_dir)``. SPOC discovers apps, loads their modules in dependency order,
manages lifecycle, and registers every declared object in one flat registry under a
canonical identifier: ``kind:namespace.object_name``. External surfaces (HTTP, CLI,
workers) are built on top by enumerating the registry — the kernel describes, it never
executes.

What follows is the whole public surface. ``spoc.core`` is **internal** — it holds the
declaration layer, the module loader, and the configuration adapter, and nothing in it
carries a stability promise, however reachable it happens to be. Anything a framework
author legitimately needs is re-exported here; if something you need is only reachable
under ``spoc.core``, that is a gap to report, not an API to import.

Tiers for every name below are declared in ``[tool.spoc.stability]`` in ``pyproject.toml``
and enforced by ``apicheck``. See the stability policy in the docs.
"""

from .__about__ import __version__
from .core.declaration import KindSpec, component
from .core.exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    ComponentKindMismatchError,
    ConfigurationError,
    DuplicateComponentError,
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

__all__ = [
    # Package
    "__version__",
    # Declaration
    "Framework",
    "KindSpec",
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
    "UnresolvedReferenceError",
    "DuplicateComponentError",
    "IdentityDivergenceError",
    "ComponentKindMismatchError",
    "MissingNameError",
    "UnmarkableObjectError",
    "MetadataContractError",
]
