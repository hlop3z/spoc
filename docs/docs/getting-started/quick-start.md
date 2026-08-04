# Quick Start

Build a minimal SPOC project: one app, one kind, resolved through the
registry.

## Project layout

```
myproject/
├── apps/
│   └── blog/
│       ├── __init__.py
│       └── models.py        # objects here are kind "models"
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── spoc.toml
├── framework.py             # composition root
└── main.py
```

Layout **is** taxonomy: objects declared in `<app>/models.py` are components
of kind `models`, and the app directory name is the namespace. The kinds are
exactly `Schema.modules` — a closed set, fixed at composition time.

## 1. Configuration

`config/spoc.toml`:

```toml
[spoc]
mode = "development"
debug = true

[spoc.apps]
production = []
staging = []
development = []

[spoc.plugins]
```

`config/settings.py`:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTALLED_APPS = ["blog"]
PLUGINS: dict = {}
```

## 2. The composition root

`framework.py`:

```python
from config import settings
from spoc import Components, Framework, Schema

# The declared, closed kind set — must match Schema.modules
components = Components("models")

SCHEMA = Schema(modules=["models"])

framework = Framework(settings.BASE_DIR, SCHEMA)
```

## 3. Declare components

`apps/blog/models.py`:

```python
from framework import components

@components.register("models")
class post:                        # snake_case name → conforms as-is
    ...

@components.register("models", name="comment_thread")
class CommentThread:               # PascalCase → explicit name required
    ...
```

!!! warning "Reject, never normalize"
    Identifier segments must match `^[a-z][a-z0-9_]*$`. A class named
    `CommentThread` registered without `name=` raises
    `InvalidSegmentError` — SPOC never silently renames anything.

## 4. Use the registry

`main.py`:

```python
from framework import framework

# Resolve one component by canonical identifier
record = framework.resolve("models:blog.post")
print(record.identifier)   # models:blog.post
print(record.kind)         # models
print(record.namespace)    # blog
print(record.name)         # post
print(record.object)       # <class 'blog.models.post'>

# Enumerate everything (deterministic order)
for component in framework.registry:
    print(component.identifier)

# Facet views are derived from the same flat store
framework.registry.by_kind("models")
framework.registry.by_namespace("blog")

framework.shutdown()
```

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
- [Framework](../core/framework.md) — the composition root in detail
- [Components](../core/components.md) — declaration rules and the identifier grammar
