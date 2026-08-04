# Dependency Management

Inter-kind load order is an attribute of a kind, so it is declared on that
kind's `KindSpec`:

```python
framework = spoc.Framework(
    "models",
    spoc.KindSpec("views", depends_on=("models",)),   # views load after models
)
```

Within every app, `<app>.models` initializes before `<app>.views`, and tears
down in the reverse order. Every entry in `depends_on` must be a declared kind
— anything else raises `UnknownKindError` at construction.

## How ordering works

The loader records each `<app>.<kind>` module as a node with its dependencies
and computes a topological order with the standard library's
`graphlib.TopologicalSorter`. Initialization walks that order; shutdown walks
it reversed.

Edges are recorded even when the dependency has not been registered yet, so
the order in which kinds are declared never silently drops one.

## Cycles are startup errors

A dependency cycle raises `CircularDependencyError` at start, naming the
modules involved:

```python
framework = spoc.Framework(
    spoc.KindSpec("a", depends_on=("b",)),
    spoc.KindSpec("b", depends_on=("a",)),
)
framework.start(BASE_DIR)
# CircularDependencyError: Circular dependency detected: app.a -> app.b -> ...
```

## Module lifecycle functions

Any app module may define `initialize()` and `teardown()` — called in
dependency order and reverse dependency order respectively. See
[Lifecycle](../advanced/lifecycle.md).
