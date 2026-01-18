"""
Dynamic Module Import, Caching & Lifecycle Management System.

This package provides tools for dynamically importing modules at runtime,
caching them efficiently, and managing their lifecycle with dependency-based
initialization and teardown.
"""

from .components import Components
from .core.config_loader import load_configuration, load_environment, load_spoc_toml
from .core.exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    LifecycleError,
    ModuleNotCachedError,
    SpocError,
)
from .core.importer import Importer
from .core.singleton import SingletonMeta, singleton
from .core.utils import DependencyGraph

# Framework
from .framework import Config, Framework, Hook, Schema
from .inject_apps import inject_apps
from .case_style import case_style

__all__ = [
    # Framework Utilities
    "Framework",
    "Config",
    "Hook",
    "Schema",
    # Core importer
    "Importer",
    # Components
    "Components",
    # Exceptions
    "SpocError",
    "AppNotFoundError",
    "ModuleNotCachedError",
    "CircularDependencyError",
    "LifecycleError",
    # Singleton
    "SingletonMeta",
    "singleton",
    # Config loaders
    "load_configuration",
    "load_environment",
    "load_spoc_toml",
    # Inject apps
    "inject_apps",
    # Utilities
    "case_style",
    "DependencyGraph",
]
