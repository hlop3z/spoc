# Lifecycle Hooks

SPOC manages startup and shutdown in dependency order. There are two hook
mechanisms: **module functions** and **schema hooks**. Both are lifecycle
only — the kernel never calls user code outside of them.

## Module lifecycle functions

Any app module may define `initialize` and `teardown`:

```python
# blog/models.py

def initialize():
    """Runs during startup, after this module's dependencies."""
    ...

def teardown():
    """Runs during shutdown, before this module's dependencies."""
    ...
```

Ordering follows the dependency graph: if `views` depends on `models`,
`models.initialize()` runs first and `models.teardown()` runs last.

## Schema hooks

Schema hooks attach per module *name*, across all apps, and receive the set
of registered objects belonging to that module:

```python
from spoc import Framework, Hook, Schema

def init_models(objects):
    # `objects` is the set of components discovered in <app>.models
    for obj in objects:
        ...

schema = Schema(
    modules=["models", "views"],
    hooks={
        "models": Hook(startup=init_models,
                       shutdown=lambda objs: print("bye", objs)),
    },
)
```

Under the hood this registers a pattern hook (`*.models`) on the framework's
importer. Hooks are instance state: two frameworks never share them.

## Custom patterns

For finer control, register hooks directly on the importer:

```python
framework.importer.register_hook(
    pattern="blog.*",              # wildcards: * and ?
    on_startup=lambda objs: ...,
    on_shutdown=lambda objs: ...,
)
```

Exact module names (no wildcard) take precedence over pattern hooks.

## Full startup order

1. Component discovery — every module's declared components register into
   the registry; any failure (kind mismatch, invalid segment, duplicate)
   aborts startup **before** any initialization side effects run
2. For each module in dependency order: startup hooks fire, then the
   module's `initialize()`
3. On `shutdown()`: for each module in reverse order, shutdown hooks fire,
   then the module's `teardown()`

## Errors

Failures during startup/shutdown surface as `SpocError` (or a more specific
subclass — `CircularDependencyError`, `ComponentKindMismatchError`,
`DuplicateComponentError`). Nothing is silently skipped.
