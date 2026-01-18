# Core Utilities API Reference

This page provides detailed API documentation for SPOC's core utility modules, including exceptions, singleton patterns, dependency management, case conversion, and path injection utilities.

## Exceptions

SPOC provides a hierarchy of custom exceptions for clear error handling and debugging.

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

### ModuleNotCachedError

::: spoc.core.exceptions.ModuleNotCachedError
    options:
      show_root_heading: true
      show_source: false

### CircularDependencyError

::: spoc.core.exceptions.CircularDependencyError
    options:
      show_root_heading: true
      show_source: false

### LifecycleError

::: spoc.core.exceptions.LifecycleError
    options:
      show_root_heading: true
      show_source: false

### ConfigurationError

::: spoc.core.exceptions.ConfigurationError
    options:
      show_root_heading: true
      show_source: false

## Singleton Pattern

SPOC provides two approaches to implementing the Singleton pattern: a metaclass and a decorator.

### SingletonMeta

::: spoc.core.singleton.SingletonMeta
    options:
      show_root_heading: true
      show_source: false

### singleton Decorator

::: spoc.core.singleton.singleton
    options:
      show_root_heading: true
      show_source: false

## Dependency Management

### DependencyGraph

::: spoc.core.utils.DependencyGraph
    options:
      show_root_heading: true
      show_source: false
      members:
        - add_node
        - add_edge
        - topological_sort
        - reversed

### Utility Functions

::: spoc.core.utils.get_attribute
    options:
      show_root_heading: true
      show_source: false

## Case Style Conversion

SPOC provides utilities to convert strings between different naming conventions.

### case_style Function

::: spoc.case_style.case_style
    options:
      show_root_heading: true
      show_source: false

### Conversion Functions

::: spoc.case_style.to_snake_case
    options:
      show_root_heading: true
      show_source: false

::: spoc.case_style.to_camel_case
    options:
      show_root_heading: true
      show_source: false

::: spoc.case_style.to_pascal_case
    options:
      show_root_heading: true
      show_source: false

::: spoc.case_style.to_kebab_case
    options:
      show_root_heading: true
      show_source: false

### Type Guards

::: spoc.case_style.is_valid_case_style
    options:
      show_root_heading: true
      show_source: false

## Path Injection

### inject_apps Function

::: spoc.inject_apps.inject_apps
    options:
      show_root_heading: true
      show_source: false

### Helper Functions

::: spoc.inject_apps.ensure_directory
    options:
      show_root_heading: true
      show_source: false

::: spoc.inject_apps.add_to_python_path
    options:
      show_root_heading: true
      show_source: false
