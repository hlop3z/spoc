# Framework

`Framework` is the **composition root**: it owns its importer (and therefore
its registry and hooks), loads configuration, discovers apps, and manages
lifecycle. Two `Framework` instances in one process are fully independent —
there is no global state.

## Construction

```python
from pathlib import Path
from spoc import Framework, Schema, Hook

schema = Schema(
    modules=["models", "views"],            # also the closed kind set
    dependencies={"views": ["models"]},     # load order within each app
    hooks={
        "models": Hook(
            startup=lambda objs: print("models up:", objs),
            shutdown=lambda objs: print("models down:", objs),
        ),
    },
)

framework = Framework(
    base_dir=Path(__file__).parent,
    schema=schema,
    mode="strict",        # raise when an app is missing a declared module
)
```

Construction runs the full startup sequence:

1. `apps/` is put on the import path
2. `spoc.toml`, settings, and the mode's environment are loaded
3. Plugins are loaded from their URIs
4. Apps are collected via the mode cascade and their modules registered
5. **Components are discovered into the registry** — loudly: a declared
   component that cannot be registered (kind mismatch, invalid segment,
   duplicate identifier) fails startup with a precise error
6. Modules initialize in dependency order, hooks firing per module

## The registry

`framework.registry` is the single read surface — one flat store of
`Component` records with derived, deterministic facet views:

```python
for component in framework.registry:          # all records, ordered
    print(component.identifier)

framework.registry.by_kind("models")          # one kind
framework.registry.by_namespace("blog")       # one app
framework.registry.namespaces("models")       # namespaces holding a kind
len(framework.registry)
"models:blog.post" in framework.registry
```

## Resolution

```python
record = framework.resolve("models:blog.post")
```

`resolve` is a **pure lookup**: the resolved object comes back unexecuted,
and the kernel never calls it. Failures are per segment, in the fixed order
kind → namespace → object_name, each naming the failing segment, its value,
and the valid candidates:

| Failure | Error |
| --- | --- |
| doesn't parse | `MalformedIdentifierError` |
| bad segment charset | `InvalidSegmentError` |
| kind not declared | `UnknownKindError` |
| no such namespace for that kind | `UnknownNamespaceError` |
| no such object in kind:namespace | `UnknownObjectError` |

There are no `None` returns anywhere in the lookup path.

## The mode cascade

`spoc.toml` declares apps per mode; lower modes include the higher ones:

```toml
[spoc]
mode = "development"

[spoc.apps]
production = ["auth"]
staging    = ["reports"]
development = ["sandbox"]
```

| mode | loads |
| --- | --- |
| `production` | `auth` |
| `staging` | `reports` + `auth` |
| `development` | `sandbox` + `reports` + `auth` |

With one app per adapter, the cascade **is** adapter selection: register the
fake engine as a development app and the real one as a production app, and
switching modes swaps the implementation — no branching.

`INSTALLED_APPS` in settings loads in every mode, first.

## Lifecycle

```python
framework.startup()     # runs automatically on construction
framework.shutdown()    # reverse dependency order, shutdown hooks fire
```

Modules may define `initialize()` / `teardown()` functions; schema hooks
receive the set of registered objects belonging to their module.

## Independence

Each framework owns its state — importer, registry, hooks, installed apps:

```python
fw_a = Framework(base_dir=project_a, schema=schema_a)
fw_b = Framework(base_dir=project_b, schema=schema_b)

fw_a.registry is fw_b.registry        # False — nothing is shared
```
