# Core Utilities API Reference

This page documents SPOC's core utility modules: exceptions, the configuration
adapter, and path injection. (Dependency ordering uses the standard library's
`graphlib` — there is no SPOC-specific graph API.)

## Exceptions

SPOC provides a hierarchy of custom exceptions for clear error handling.
Identifier and registry errors are documented on the
[Registry API](registry.md) page.

### SpocError

::: spoc.core.exceptions.SpocError
    options:
      show_root_heading: true
      show_source: false

### AppNotFoundError

::: spoc.core.exceptions.AppNotFoundError
    options:
      show_root_heading: true
      show_source: false

### MissingModuleError

Raised when an app provides no module for a kind whose modules are required.
Declaring the kind with `required=False` on its
[`KindSpec`](components.md#spoc.core.declaration.KindSpec) makes the absence legal.

::: spoc.core.exceptions.MissingModuleError
    options:
      show_root_heading: true
      show_source: false

### CircularDependencyError

::: spoc.core.exceptions.CircularDependencyError
    options:
      show_root_heading: true
      show_source: false

### ConfigurationError

::: spoc.core.exceptions.ConfigurationError
    options:
      show_root_heading: true
      show_source: false

## Configuration

`spoc.toml` is the only configuration file the kernel reads. Absent keys fall back
to defaults; a missing file loads as all defaults with a warning.

::: spoc.core.config.load_spoc_toml
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.config.load_environment
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.config.validate_spoc_config
    options:
      show_root_heading: true
      show_source: false

## Path Injection

### inject_apps Function

::: spoc.core.paths.inject_apps
    options:
      show_root_heading: true
      show_source: false

### eject_apps Function

::: spoc.core.paths.eject_apps
    options:
      show_root_heading: true
      show_source: false
