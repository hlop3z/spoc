# Framework

`Framework` is the **single declaration point** and the composition root. It
owns the registry, the loader, and the configuration adapter, and it is the
only place they are wired together. Two `Framework` instances in one process
are fully independent — there is no global state.

## Declaration

Every attribute of a kind lives on its `KindSpec`. A bare string is shorthand
for a spec with all defaults, so simple kinds stay simple:

```python
from dataclasses import dataclass
import spoc

@dataclass(frozen=True)
class ModelMeta:
    table: str

framework = spoc.Framework(
    spoc.KindSpec("models", metadata=ModelMeta),
    spoc.KindSpec("views", depends_on=("models",), required=False),
    "commands",                              # shorthand: all defaults
)

model = framework.kind("models")             # ready-made decorators
view = framework.kind("views")
```

Construction is **inert**: no filesystem access, no `sys.path` changes, no
imports. It only records the declaration — which is why app modules can
safely import the decorators before anything has started.

- Kinds are identifier segments: lowercase snake_case, validated, never
  normalized.
- `depends_on` entries must be declared kinds — anything else raises
  `UnknownKindError` immediately.
- `required` defaults to `True`, so tolerating a missing module is always a
  deliberate act. It is decided per kind: declaring `views` optional does not
  weaken the guarantee for `models`.
- `framework.kind("controllers")` on an undeclared kind raises
  `UnknownKindError` naming the declared set.

## Registration decorators

The callable returned by `framework.kind()` supports both forms:

```python
@model(meta=ModelMeta(table="posts"))   # metadata must match the kind's contract
class Post: ...

@model(name="legacy_user", meta=ModelMeta(table="users"))
class OldAccount: ...                   # a stated name is verbatim and validated

@view                                   # ListPosts → views:<app>.list_posts
class ListPosts: ...                    # `views` declares no contract, so no meta
```

A kind that declares a `metadata` type has every component checked against it
at registration. A kind that declares none accepts no metadata at all — there
is no untyped channel to fall back on.

The name is derived from the object in snake_case; pass `name=` only to
override it. Lookup never converts — `models:blog.user_account` is the one
canonical identifier.

## Lifecycle

```python
framework.start(BASE_DIR)     # boots the project — the only step with side effects
framework.started             # True after a successful start
framework.shutdown()          # reverse-order teardown; no-op if never started
```

`shutdown()` returns the framework to its inert pre-start state — empty
registry, no loaded modules, the injected import path removed — so a later
`start()` on the same or a different project is a clean boot. A *failed*
`start()` does the same on its way out: modules that came up are torn down
and the framework stays inert, so the caller can fix the cause and retry.

`start(base_dir)` runs, in order:

1. `apps/` is put on the import path
2. `config/spoc.toml` is loaded — the only file the kernel reads
3. Plugins are loaded from `[spoc.plugins]` and registered into the registry —
   each group must name a declared kind, and a bad reference fails start
4. Apps are collected via the mode cascade and their modules registered. A
   mode (or `[spoc.apps]` key) that names no known mode raises
   `ConfigurationError`. A module absent for a required kind raises
   `MissingModuleError`; absent for an optional one it is skipped. An app
   package that does not exist at all raises `AppNotFoundError`, whatever the
   optionality. A module that exists but fails to import is an error either way
5. **Components are discovered into the registry** — loudly: a declared
   component that cannot be registered (kind mismatch, invalid segment,
   duplicate identifier, metadata departing from its kind's contract) fails
   start with a precise error
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

Hooks are a kind attribute, so they ride the `KindSpec` like every other one:

```python
def init_models(objects):        # the set of the module's registered objects
    ...

def close_models(objects):
    ...

framework = spoc.Framework(
    spoc.KindSpec("models", on_startup=init_models, on_shutdown=close_models),
)
```

Hooks fire for every app's module of that kind — see
[Lifecycle](../advanced/lifecycle.md) for ordering details.

## Reads

```python
framework.resolve("models:blog.post")    # one record, precise per-segment failures
framework.registry                       # the flat store — enumerate, by_kind, by_namespace
framework.installed_apps                 # the cascaded app list, after start
framework.config.project                 # the [spoc] table
framework.config.environment             # the mode's environment values
```

The kernel **describes; it never executes** — `resolve` returns the record
with its object unexecuted. Invocation belongs to the surfaces built on top.
