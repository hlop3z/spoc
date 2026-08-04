# Loader API Reference

The loader imports an application's modules in dependency order and runs their
lifecycle. It is deliberately **kind-blind**: it is handed a kind label with each
module and carries it back out for hook dispatch, but never reads or decides
anything from it. That is what keeps the registry — a pure core concern — out of
the loader entirely.

It handles:

- **Dynamic module loading** at runtime
- **Dependency-ordered** initialization and reverse-ordered teardown
- **Per-kind lifecycle hooks**, dispatched by the label the caller supplied
- **Absent vs. broken** module discrimination

Each `Framework` owns one loader instance; nothing is shared between frameworks.
The loader is not exported from the `spoc` package — it is reachable at
`spoc.core.loader` for anyone extending the kernel.

## Loader Class

::: spoc.core.loader.Loader
    options:
      show_root_heading: true
      show_source: false
      members:
        - register
        - load_from_uri
        - ordered
        - initialize
        - shutdown

## LoadedModule

::: spoc.core.loader.LoadedModule
    options:
      show_root_heading: true
      show_source: false

## Component Discovery

Discovery turns the declaration markers in a loaded module into registry records.
It lives in the declaration layer, not the loader — it takes a module and a
registry, and reaches into no cache.

::: spoc.core.declaration.discover
    options:
      show_root_heading: true
      show_source: false

## Related Exceptions

The loader may raise the following exceptions:

- **[SpocError](core-utils.md#spoc.core.exceptions.SpocError)** - Base exception for all SPOC errors
- **[AppNotFoundError](core-utils.md#spoc.core.exceptions.AppNotFoundError)** - Raised when a module cannot be found
- **[MissingModuleError](core-utils.md#spoc.core.exceptions.MissingModuleError)** - Raised when a required kind's module is absent
- **[CircularDependencyError](core-utils.md#spoc.core.exceptions.CircularDependencyError)** - Raised when circular dependencies are detected
- **[ComponentKindMismatchError](registry.md)** and the other registration errors — see the [Registry API](registry.md)

See [Core Utilities](core-utils.md) for full exception documentation.
