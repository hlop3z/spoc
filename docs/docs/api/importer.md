# Importer API Reference

This page provides detailed API documentation for the Importer module in SPOC.

The Importer is central to SPOC, enabling dynamic, dependency-aware module management. It handles:

- **Dynamic module loading** at runtime
- **Caching** for efficient module reuse
- **Lifecycle management** with dependency-ordered initialization and teardown
- **Hook registration** for custom startup/shutdown behavior

## Importer Class

::: spoc.core.importer.Importer
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - load
        - register
        - register_hook
        - load_from_uri
        - has
        - get
        - clear
        - clear_all
        - unload_all
        - startup
        - shutdown
        - keys
        - components

## ModuleInfo Class

::: spoc.core.importer.ModuleInfo
    options:
      show_root_heading: true
      show_source: false

## Related Exceptions

The Importer may raise the following exceptions:

- **[SpocError](core-utils.md#spoc.core.exceptions.SpocError)** - Base exception for all SPOC errors
- **[AppNotFoundError](core-utils.md#spoc.core.exceptions.AppNotFoundError)** - Raised when a module cannot be found
- **[ModuleNotCachedError](core-utils.md#spoc.core.exceptions.ModuleNotCachedError)** - Raised when accessing a module not in cache
- **[CircularDependencyError](core-utils.md#spoc.core.exceptions.CircularDependencyError)** - Raised when circular dependencies are detected

See [Core Utilities](core-utils.md) for full exception documentation. 