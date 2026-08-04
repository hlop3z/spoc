# Lifecycle

SPOC manages startup and shutdown in dependency order. There are three
lifecycle mechanisms, all declared on the framework object or in app
modules — the kernel never calls user code outside of them.

## on_ready — the finalize phase

Registered with a decorator, fired exactly once per start, after **all**
components are registered and before any module initializes:

```python
@framework.on_ready
def build_derived_state(registry):
    # the completed registry: every component of every kind
    for record in registry.by_kind("models"):
        ...
```

- Callbacks fire in registration order.
- A callback error fails `start()` — the framework is not reported started.
- This is the home for cross-component builds (ORM tables, route trees,
  DI graphs). Never do that work as an import side effect.

## Per-kind hooks

Fire for every app's module of a kind, with the set of that module's
registered component objects:

```python
@framework.on_startup("models")
def init_models(objects):
    ...

@framework.on_shutdown("models")
def close_models(objects):
    ...
```

Startup hooks fire before the module's own `initialize()`; shutdown hooks
before its `teardown()`. Hooks are instance state — two frameworks never
share them.

For finer control, register a pattern hook directly on the importer:

```python
framework.importer.register_hook(
    pattern="blog.*",              # wildcards: * and ?
    on_startup=lambda objs: ...,
    on_shutdown=lambda objs: ...,
)
```

An exact-name hook overrides pattern hooks per hook type; pattern hooks
still fire for hook types the exact-name entry does not define.

## Module lifecycle functions

Any app module may define `initialize` and `teardown`:

```python
# blog/models.py

def initialize():
    """Runs during startup, after this module's dependencies."""

def teardown():
    """Runs during shutdown, before this module's dependencies."""
```

## Full start order

1. Plugins load from `[spoc.plugins]`
2. Component discovery — every module's declared components register into
   the registry; any failure (kind mismatch, invalid segment, duplicate)
   aborts start **before** any initialization side effects run
3. `on_ready` callbacks fire with the completed registry
4. For each module in dependency order: startup hooks fire, then the
   module's `initialize()`
5. On `shutdown()`: for each module in reverse order, shutdown hooks fire,
   then the module's `teardown()`

## Errors

Failures during start/shutdown surface as `SpocError` (or a more specific
subclass — `CircularDependencyError`, `ComponentKindMismatchError`,
`DuplicateComponentError`). Nothing is silently skipped, and a failed start
leaves `framework.started` False.
