# Importer

The `Importer` is the machinery under `Framework`: dynamic module loading
with caching, dependency-ordered lifecycle, and component discovery into the
registry. You rarely use it directly — the framework owns one instance — but
it is public for advanced composition.

Each instance is fully independent: cache, dependency graph, hooks, and
registry are all instance state.

## Basic usage

```python
from spoc import Importer

importer = Importer(kinds=("models",))          # closed kind set for its registry
importer.register("blog.models", dependencies=["blog.utils"])
importer.startup()      # discovery + initialize in dependency order
...
importer.shutdown()     # teardown in reverse order
```

## Module lifecycle

- `register(name, dependencies=[...])` loads a module and records its edges
  in the dependency graph
- `startup()` first discovers every declared component into the registry
  (loudly — see below), then initializes modules in topological order,
  calling each module's `initialize()` if present and firing matching hooks
- `shutdown()` tears down in reverse order, calling `teardown()` if present
- Circular dependencies raise `CircularDependencyError`

In `strict` mode a missing module raises `AppNotFoundError`; in `loose` mode
it is skipped.

## Component discovery

At startup, each registered module `<app>.<kind>` is scanned for objects
carrying a SPOC declaration marker:

- the app package name becomes the `namespace` segment
- the module file name is the `kind` — a declared kind that doesn't match
  raises `ComponentKindMismatchError` naming the object, both kinds, and the
  file
- classes and functions imported from elsewhere are skipped (they register
  where they are defined)
- duplicates raise `DuplicateComponentError`

Discovery runs for **all** modules before any module initializes, so
registration errors surface before any initialization side effects run.

The result lands in `importer.registry` — see the
[Registry API](../api/registry.md).

## Hooks

```python
importer.register_hook(
    pattern="*.models",                  # wildcard per module name
    on_startup=lambda objs: ...,         # receives the module's registered objects
    on_shutdown=lambda objs: ...,
)
```

Hooks are instance state — two importers never share them.

## Loading helpers

```python
importer.load("blog.models")             # import + cache
importer.load_from_uri("blog.extras.hook")   # load an attribute by URI
importer.get("blog.models")              # cached module (raises if absent)
importer.has("blog.models")
importer.keys()
importer.clear("blog.models")            # drop from cache (teardown if needed)
importer.unload_all()                    # full teardown + sys.modules removal
```
