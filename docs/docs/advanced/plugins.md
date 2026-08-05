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
then `apps`, the top-level package). A group that is not a declared kind
fails start with `UnknownKindError`: configuration populates the kind set,
it never widens it.

## Identity

A plugin's identifier follows the same grammar discovery uses: the group is
the kind, the reference's top-level package is the namespace, and the
attribute derives the object name (PEP 8 names become snake_case, exactly as
class names do under a decorator):

```
hooks = ["extras.hook"]             →  hooks:extras.hook
middleware = ["auth.extras.Audit"]  →  middleware:auth.audit
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
