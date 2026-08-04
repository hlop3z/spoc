# Framework

`Framework` is the **single declaration point** and the composition root: the
kind set, inter-kind dependencies, and lifecycle hooks are stated once, on
one object. It owns its importer (and therefore its registry and hooks).
Two `Framework` instances in one process are fully independent — there is no
global state.

## Declaration

```python
import spoc

framework = spoc.Framework(
    "models", "views",                      # the closed kind set
    dependencies={"views": ["models"]},     # load order within each app
    mode="strict",                          # raise when an app misses a module
)

model = framework.kind("models")            # ready-made decorators
view = framework.kind("views")
```

Construction is **inert**: no filesystem access, no `sys.path` changes, no
imports. It only records the declaration — which is why app modules can
safely import the decorators before anything has started.

- Kinds are identifier segments: lowercase snake_case, validated, never
  normalized.
- `dependencies` keys and values must be declared kinds — anything else
  raises `UnknownKindError` immediately.
- `framework.kind("controllers")` on an undeclared kind raises
  `UnknownKindError` naming the declared set.

## Registration decorators

The callable returned by `framework.kind()` supports both forms:

```python
@model                        # name taken from the object (must conform)
class post: ...

@model(name="user_account")   # explicit conforming name
class UserAccount: ...

@model(config={"table": "posts"}, metadata={"public": True})
class tag: ...                # config/metadata ride onto the registry record
```

## Lifecycle

```python
framework.start(BASE_DIR)     # boots the project — the only step with side effects
framework.started             # True after a successful start
framework.shutdown()          # reverse-order teardown; no-op if never started
```

`start(base_dir)` runs, in order:

1. `apps/` is put on the import path
2. `config/spoc.toml` is loaded — the only file the kernel reads
3. Plugins are loaded from `[spoc.plugins]` (a bad reference fails start)
4. Apps are collected via the mode cascade and their modules registered
5. **Components are discovered into the registry** — loudly: a declared
   component that cannot be registered (kind mismatch, invalid segment,
   duplicate identifier) fails start with a precise error
6. **`on_ready` callbacks fire** with the completed registry
7. Modules initialize in dependency order, firing per-kind startup hooks

Starting an already-started framework raises `SpocError`.

## on_ready — the finalize phase

Anything that needs to see *all* components at once — ORM table building,
route trees, DI graphs — belongs in an `on_ready` callback, not in an import
side effect:

```python
@framework.on_ready
def build_tables(registry):
    for record in registry.by_kind("models"):
        ...
```

Callbacks fire exactly once per start, in registration order, after
discovery and before module initialization. A callback error fails start.

## Per-kind lifecycle hooks

```python
@framework.on_startup("models")
def init_models(objects):        # the set of the module's registered objects
    ...

@framework.on_shutdown("models")
def close_models(objects):
    ...
```

Hooks fire for every app's module of that kind — see
[Lifecycle](../advanced/lifecycle.md) for ordering details.

## Reads

```python
framework.resolve("models:blog.post")    # one record, precise per-segment failures
framework.registry                       # the flat store — enumerate, by_kind, by_namespace
framework.installed_apps                 # the cascaded app list, after start
framework.plugins                        # loaded plugin groups, after start
framework.config.project                 # the [spoc] table
framework.config.environment             # the mode's environment values
```

The kernel **describes; it never executes** — `resolve` returns the record
with its object unexecuted. Invocation belongs to the surfaces built on top.
