# Importer API Reference

The Importer enables dynamic, dependency-aware module management. It handles:

- **Dynamic module loading** at runtime
- **Caching** for efficient module reuse
- **Lifecycle management** with dependency-ordered initialization and teardown
- **Component discovery** into the flat registry at startup
- **Hook registration** for custom startup/shutdown behavior

Each Importer instance is fully independent — cache, graph, hooks, and
registry are all instance state.

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

## ModuleInfo Class

::: spoc.core.importer.ModuleInfo
    options:
      show_root_heading: true
      show_source: false

## Component Discovery

::: spoc.core.components_discovery.discover_components
    options:
      show_root_heading: true
      show_source: false

## Related Exceptions

The Importer may raise the following exceptions:

- **[SpocError](core-utils.md#spoc.core.exceptions.SpocError)** - Base exception for all SPOC errors
- **[AppNotFoundError](core-utils.md#spoc.core.exceptions.AppNotFoundError)** - Raised when a module cannot be found
- **[ModuleNotCachedError](core-utils.md#spoc.core.exceptions.ModuleNotCachedError)** - Raised when accessing a module not in cache
- **[CircularDependencyError](core-utils.md#spoc.core.exceptions.CircularDependencyError)** - Raised when circular dependencies are detected
- **[ComponentKindMismatchError](registry.md)** and the other registration errors — see the [Registry API](registry.md)

See [Core Utilities](core-utils.md) for full exception documentation.
