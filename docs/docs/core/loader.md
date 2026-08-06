# Loader

The `Loader` is the machinery under `Framework`: it imports an application's
modules in dependency order and runs their lifecycle. You rarely touch it — the
framework owns one instance and wires it — but it is reachable at
`spoc.core.loader` for advanced composition.

It is deliberately **kind-blind**. It is handed a kind label with each module and
carries it back out for hook dispatch, but never reads or decides anything from
it. That is what keeps the registry — a pure core concern — out of the loader
entirely: the loader has never seen a registry, and discovery is not its job.

Each instance is fully independent: module table, dependency graph, and state are
all per-instance.

## Basic usage

```python
from spoc.core.loader import Loader

loader = Loader()
loader.register("apps.blog.models", kind="models", app="apps.blog", namespace="blog")
loader.register(
    "apps.blog.views",
    kind="views",
    app="apps.blog",
    namespace="blog",
    dependencies=("apps.blog.models",),
)

for entry in loader.ordered():           # dependency order, dependencies first
    ...                                  # entry.name, entry.module, entry.kind

loader.initialize(hooks, components_for)
loader.shutdown(hooks, components_for)
```

`initialize` and `shutdown` take the per-kind hook table and a callable that maps
a loaded module to its registered component objects. Both are supplied by
`Framework` — that inversion is what lets the loader fire registry-aware hooks
without knowing the registry exists.

## Module lifecycle

- `register(name, kind=..., app=..., namespace=..., dependencies=..., required=...)`
  imports a module exactly as named, through the normal import system — the
  loader never alters the import environment to make a name resolvable — and
  records its edges in the dependency graph. Edges are recorded even when the
  dependency has not been registered yet, so registration order never
  silently drops one
- `ordered()` returns the modules in topological order; circular dependencies
  raise `CircularDependencyError`
- `initialize(...)` fires each module's startup hook, then its own
  `initialize()` if present
- `shutdown(...)` walks in reverse, firing shutdown hooks then `teardown()`.
  The two halves are tracked separately, so a module whose own `initialize()`
  raised *after* its startup hook fired still gets the paired shutdown hook —
  and no `teardown()` for an `initialize()` that never completed
- `ainitialize(...)` and `ashutdown(...)` are the awaiting twins: hooks and
  module functions that are coroutine functions are awaited. The sync pair
  refuses a coroutine loudly with `SpocError` — it never skips or half-runs
  one
- a failure raised by a hook or a module's own `initialize()`/`teardown()`
  is the app author's, and propagates untouched — the kernel never wraps it

## Absent is not broken

Whether a missing module is an error is decided by the declaring kind's
`required` flag, passed in per registration — there is no framework-wide switch.

| Situation | Result |
| --------- | ------ |
| Module absent, kind is required | `MissingModuleError` naming the app, kind, and expected module |
| Module absent, kind is optional | Skipped; the app contributes nothing of that kind |
| The app package itself does not exist | `AppNotFoundError`, whatever the optionality — `required` lets an existing app omit a kind, it cannot excuse a missing app |
| Module present but raises on import | Always an error, whatever the optionality — the author's own exception propagates with its traceback |

The distinction is made from which module the import system reports as missing:
the module being registered is absent; a parent package of it means the app
itself is absent; anything else means the module exists and its own imports are
broken.

## Component discovery

Discovery is **not** part of the loader. It lives in the declaration layer and
takes a loaded module plus a registry, reaching into no cache. `Framework` walks
`loader.ordered()` and calls it per module.

For each module `<app>.<kind>`, objects carrying a declaration marker are
registered:

- the final segment of the declared app path becomes the `namespace` segment
- the module file name is the `kind` — a declared kind that doesn't match raises
  `ComponentKindMismatchError` naming the object, both kinds, and the file
- only the object the decorator was applied to declares: instances and
  subclasses of a decorated class inherit the marker but are not components
- a marked object found in a module of *another* kind is a use, not a claim, and
  is skipped; classes and functions carry `__module__`, so a re-export registers
  where it was defined
- a marked *instance* found in a second module of the **same** kind is a second
  claim over one object and raises `IdentityDivergenceError` naming both
  identities — load order never gets to pick the namespace
- duplicates raise `DuplicateComponentError`; re-registration under the same
  identity is idempotent

Discovery runs for **all** modules before any module initializes, so registration
errors surface before any initialization side effects run. The result lands in
`framework.registry` — see the [Registry API](../api/registry.md).

## Loading helpers

```python
loader.load_from_uri("blog.extras.hook")   # load an attribute by dotted reference
len(loader)                                # how many modules are loaded
list(loader)                               # LoadedModule entries, in dependency order
```

`load_from_uri` fails the same way registration does: an absent module raises
`AppNotFoundError`, a malformed reference or a missing attribute raises
`UnresolvedReferenceError`, and a module that exists but fails to import
propagates its own exception.
