# Plugins

Plugins are loadable references declared in `spoc.toml` — the way to pull in
objects that are *configured*, not discovered. Unlike components found by
scanning app modules, plugins are explicit: a kind and a
`package.module.attribute` reference. What they are **not** is a second
registry — a loaded plugin registers in the same flat registry as everything
else, under the same `kind:namespace.object_name` grammar.

## Declaring

Each `[spoc.plugins]` group names a **declared kind**. A kind that only
plugins populate is declared `required=False`, so apps need not provide a
module for it:

```python
framework = spoc.Framework(
    "models",
    spoc.KindSpec("middleware", required=False),
    spoc.KindSpec("hooks", required=False),
)
```

```toml
# config/spoc.toml
[spoc.plugins]
middleware = ["extras.middleware", "auth.extras.audit"]
hooks      = ["extras.hook"]
```

A reference resolves through Python's normal import system and must be
importable exactly as written — a top-level module of the project
(`extras.middleware`), an installed package (`auth.extras.audit`), or a
module inside an app (`apps.demo.extras.middleware` — whose namespace is
then `demo`, the app's own segment, never the `apps` container). A group
that is not a declared kind fails start with `UnknownKindError`:
configuration populates the kind set, it never widens it.

A kind that declares a `metadata` contract cannot be populated this way. A
configured reference is a name in a file, with nowhere to carry metadata, so
naming such a kind under `[spoc.plugins]` fails start with
`ConfigurationError` — register those components from an app module, where
metadata is passed at declaration.

## Identity

A plugin's identifier follows the same grammar discovery uses. Discovery
reads `<app>/<kind>.py` and takes the app's final segment as the namespace;
a plugin reference reads the same way — `<app_path>.<module>.<attribute>` —
so the segment before the module is the namespace (a top-level module is its
own namespace), and the attribute derives the object name (PEP 8 names
become snake_case, exactly as class names do under a decorator):

```
hooks = ["extras.hook"]                 →  hooks:extras.hook
middleware = ["auth.extras.Audit"]      →  middleware:auth.audit
hooks = ["apps.demo.extras.AuditHook"]  →  hooks:demo.audit_hook
```

## Loading

Plugins load during `start()`, in declaration order, before app modules
initialize. A reference that cannot be resolved **fails start**, naming the
reference — never a silent skip:

```python
framework.start(BASE_DIR)

framework.resolve("hooks:extras.hook").object     # the loaded object, unexecuted
framework.registry.by_kind("middleware")          # enumerate a whole group
```

The kernel loads and registers the objects; it never calls them. What a
"middleware" or "hook" *does* is defined by the surface you build on top.

Plugins register, but they never trigger lifecycle hooks. A kind's
`on_startup`/`on_shutdown` fire once per loaded *module* of that kind, and a
configured reference is not a module — so a kind only plugins populate never
fires its hooks (see [Lifecycle](lifecycle.md#per-kind-hooks)).
