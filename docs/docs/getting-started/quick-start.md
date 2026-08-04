# Quick Start

Build a minimal SPOC project: one app, one kind, resolved through the
registry. There is one way to do this — declare, mark, start.

## Project layout

```
myproject/
├── apps/
│   └── blog/
│       ├── __init__.py
│       └── models.py        # objects here are kind "models"
├── config/
│   └── spoc.toml            # the only file the kernel reads
├── framework.py             # the whole framework definition
└── main.py
```

Layout **is** taxonomy: objects declared in `<app>/models.py` are components
of kind `models`, and the app directory name is the namespace.

## 1. Declare the framework

`framework.py` — the kind set is stated exactly once, here:

```python
import spoc

framework = spoc.Framework("models")

model = framework.kind("models")
```

That's the entire framework definition. `framework.kind()` returns a
ready-made decorator; asking for an undeclared kind raises
`UnknownKindError` naming the declared set.

## 2. Configure

`config/spoc.toml`:

```toml
[spoc]
mode = "development"

[spoc.apps]
development = ["blog"]
```

Every key is optional — absent keys use defaults. No `settings.py` is
needed; if you have one, it is yours and SPOC never reads it.

## 3. Declare components

`apps/blog/models.py`:

```python
from framework import model

@model
class Post:                        # → models:blog.post
    ...

@model
class CommentThread:               # → models:blog.comment_thread
    ...
```

Write normal PEP 8 Python. The identifier is derived from the class name in
snake_case, so `CommentThread` becomes `comment_thread` — no restating it.
Functions work the same way (`def list_posts` → `list_posts`).

Pass `name=` only when you want an identifier that *differs* from the object's
name. A name you state is used verbatim and validated, never converted:

```python
@model(name="legacy_user")         # → models:blog.legacy_user
class UserAccount:
    ...

@model(name="LegacyUser")          # InvalidSegmentError — you stated it, so it must conform
class Other:
    ...
```

!!! note "Derivation converts; nothing else does"
    Conversion happens once, when deriving a name from the object. Lookups
    are exact — `resolve("models:blog.Post")` fails, because
    `models:blog.post` is the one canonical identifier.

## 4. Start and use the registry

`main.py`:

```python
from pathlib import Path
from framework import framework

framework.start(Path(__file__).resolve().parent)

# Resolve one component by canonical identifier
record = framework.resolve("models:blog.post")
print(record.identifier)   # models:blog.post
print(record.kind)         # models
print(record.namespace)    # blog
print(record.name)         # post
print(record.object)       # <class 'blog.models.Post'>

# Enumerate everything (deterministic order)
for component in framework.registry:
    print(component.identifier)

# Facet views are derived from the same flat store
framework.registry.by_kind("models")
framework.registry.by_namespace("blog")

framework.shutdown()
```

Construction is inert — nothing happens until `start(base_dir)`. Starting
twice raises; `shutdown()` before `start()` is a harmless no-op.

## Precise failures

A typo never falls through to `None` — every failed resolution names the
failing segment and the valid candidates:

```python
framework.resolve("modle:blog.post")
# UnknownKindError: Unknown kind 'modle'. Declared kinds: models

framework.resolve("models:blogg.post")
# UnknownNamespaceError: Unknown namespace 'blogg' for kind 'models'.
# Namespaces with 'models' components: blog

framework.resolve("models:blog.pots")
# UnknownObjectError: Unknown object_name 'pots' in models:blog.
# Registered: comment_thread, post

framework.resolve("models:blog.post.create")
# MalformedIdentifierError: an operation suffix is not part of the grammar
```

## Project a surface from the registry

The registry record carries everything a surface needs — build routes without
touching kernel internals:

```python
def build_routes(registry):
    return [
        {"method": "GET", "path": f"/{c.namespace}/{c.name}", "endpoint": c.object}
        for c in registry.by_kind("views")
    ]
```

See the [Basic Example](../examples/basic.md) for the full working project,
including a FastAPI projection.

## Next steps

- [Configuration](configuration.md) — modes, environments, and the app cascade
- [Framework](../core/framework.md) — declaration and lifecycle in detail
- [Components](../core/components.md) — declaration rules and the identifier grammar
