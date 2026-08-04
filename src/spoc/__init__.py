"""
SPOC — a registry-first runtime kernel for modular monolithic applications.

SPOC discovers apps, loads their modules in dependency order, manages
lifecycle, and registers every declared object in one flat registry under a
canonical identifier: ``kind:namespace.object_name``. External surfaces
(HTTP, CLI, workers) are built on top by enumerating the registry — the
kernel describes, it never executes.
"""

from .case_style import case_style
from .components import Components, Internal, component, get_info, is_spoc
from .core.config_loader import load_configuration, load_environment, load_spoc_toml
from .core.exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    ComponentKindMismatchError,
    ConfigurationError,
    DuplicateComponentError,
    InvalidSegmentError,
    LifecycleError,
    MalformedIdentifierError,
    MissingNameError,
    ModuleNotCachedError,
    SpocError,
    UnknownKindError,
    UnknownNamespaceError,
    UnknownObjectError,
)
from .core.identifier import Identifier, compose, parse
from .core.importer import Importer
from .core.registry import Component, Registry
from .core.utils import DependencyGraph
from .framework import Config, Framework, Hook, Schema
from .inject_apps import inject_apps

__all__ = [
    # Framework
    "Framework",
    "Config",
    "Hook",
    "Schema",
    # Registry
    "Registry",
    "Component",
    # Identity
    "Identifier",
    "parse",
    "compose",
    # Declaration
    "Components",
    "Internal",
    "component",
    "get_info",
    "is_spoc",
    # Core importer
    "Importer",
    # Exceptions
    "SpocError",
    "AppNotFoundError",
    "ModuleNotCachedError",
    "CircularDependencyError",
    "LifecycleError",
    "ConfigurationError",
    "MalformedIdentifierError",
    "InvalidSegmentError",
    "UnknownKindError",
    "UnknownNamespaceError",
    "UnknownObjectError",
    "DuplicateComponentError",
    "ComponentKindMismatchError",
    "MissingNameError",
    # Config loaders
    "load_configuration",
    "load_environment",
    "load_spoc_toml",
    # Utilities
    "inject_apps",
    "case_style",
    "DependencyGraph",
]
