# Dependency Management

Inter-kind load order is declared once, on the framework object:

```python
framework = spoc.Framework(
    "models", "views",
    dependencies={"views": ["models"]},   # views load after models
)
```

Within every app, `<app>.models` initializes before `<app>.views`, and tears
down in the reverse order. Keys and values must be declared kinds — anything
else raises `UnknownKindError` at construction.

## How ordering works

The importer records each `<app>.<kind>` module as a node with its
dependencies and computes a topological order with the standard library's
`graphlib.TopologicalSorter`. Initialization walks that order; shutdown
walks it reversed.

## Cycles are startup errors

A dependency cycle raises `CircularDependencyError` at start, naming the
modules involved:

```python
spoc.Framework("a", "b", dependencies={"a": ["b"], "b": ["a"]})
framework.start(BASE_DIR)
# CircularDependencyError: Circular dependency detected: app.a -> app.b -> ...
```

## Module lifecycle functions

Any app module may define `initialize()` and `teardown()` — called in
dependency order and reverse dependency order respectively. See
[Lifecycle](../advanced/lifecycle.md).
