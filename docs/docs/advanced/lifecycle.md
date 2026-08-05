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

Hooks are an attribute of a kind, so they are declared on its `KindSpec` —
the same place its dependencies, optionality, and metadata contract live.
They fire for every app's module of that kind, with that module's registered
component objects as an immutable tuple, ordered by canonical identifier —
the same order registry enumeration yields, identical on every start:

```python
import spoc

def init_models(objects):
    ...

def close_models(objects):
    ...

framework = spoc.Framework(
    spoc.KindSpec("models", on_startup=init_models, on_shutdown=close_models),
)
```

Startup hooks fire before the module's own `initialize()`; shutdown hooks
before its `teardown()`. Hooks are instance state — two frameworks never
share them.

There is no decorator form. Every attribute of a kind is stated on the kind
it describes, so no second surface can disagree with the declaration. The
practical consequence is ordering: a hook function must be defined before the
`Framework(...)` call that references it.

## Module lifecycle functions

Any app module may define `initialize` and `teardown`:

```python
# apps/blog/models.py

def initialize():
    """Runs during startup, after this module's dependencies."""

def teardown():
    """Runs during shutdown, before this module's dependencies."""
```

## Async lifecycle

`astart(base_dir)` and `ashutdown()` mirror `start()`/`shutdown()` — the
same sequence, the same guarantees. `KindSpec` `on_startup`/`on_shutdown`
hooks and module `initialize()`/`teardown()` may be coroutine functions; the
async path awaits them:

```python
# apps/blog/models.py

async def initialize():
    """Awaited by astart(), after this module's dependencies."""
```

```python
await framework.astart(BASE_DIR)
await framework.ashutdown()
```

The sync path refuses a coroutine hook or module function **loudly**: it
raises `SpocError` naming the offender and pointing at
`astart()`/`ashutdown()`. It never skips or half-runs one. Sync hooks work
on either path.

## Full start order

1. Plugins load from `[spoc.plugins]` and register into the registry
   (each group must name a declared kind)
2. App modules import in dependency order. A module absent for a kind
   declared `required=False` is skipped; absent for a required kind it raises
   `MissingModuleError`. A module that exists but raises while importing is
   always an error, whatever its kind's optionality
3. Component discovery — every module's declared components register into
   the registry; any failure (kind mismatch, invalid segment, duplicate,
   identity divergence, metadata that departs from its kind's contract)
   aborts start **before** any initialization side effects run
4. `on_ready` callbacks fire with the completed registry
5. For each module in dependency order: startup hooks fire, then the
   module's `initialize()`
6. On `shutdown()`: for each module in reverse order, shutdown hooks fire,
   then the module's `teardown()` — then the framework resets everything the
   kernel owns: registry, loader bookkeeping, config. Python's module cache
   and module-level state persist — module-level code runs at most once per
   process, and a second `start()` re-runs discovery against the cached
   modules

## Concurrency

Decorating and marking objects is thread-safe. `start()` and `shutdown()`
are serialized — racing starts produce exactly one winner, and the losers
get the already-started error. Registry registrations are atomic and lose
nothing under concurrency, and reads after a completed start need no
coordination.

## Errors

Failures the kernel itself produces surface as `SpocError` (or a more specific
subclass — `CircularDependencyError`, `ComponentKindMismatchError`,
`DuplicateComponentError`, `MissingModuleError`, `ConfigurationError`,
`MetadataContractError`). Failures authored by app code are not the kernel's,
and propagate as themselves: a module that raises while *importing*, a lifecycle
hook that raises, and a module `initialize()`/`teardown()` that raises all
surface with their own type and traceback — the author needs their traceback,
not a wrapper around it.

Nothing is silently skipped, and a failed start rolls itself back: modules
that initialized are torn down in reverse, the framework returns to its inert
pre-start state, and `framework.started` stays False — fix the cause and call
`start()` again.
