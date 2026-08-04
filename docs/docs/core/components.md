# Components

Components are the objects SPOC manages: classes, functions, or instances
declared under a **kind** and registered in the flat registry under a
canonical identifier.

## The identifier grammar

```
kind:namespace.object_name
```

| Segment | Comes from | Example |
| --- | --- | --- |
| `kind` | the module file the object lives in (`models.py` → `models`) | `models` |
| `namespace` | the app package name | `blog` |
| `object_name` | the declared name | `post` |

Every segment must match `^[a-z][a-z0-9_]*$` (lowercase snake_case). There
are exactly three segments — an operation suffix is malformed by design.

**Derived names convert; stated names don't.** Write PEP 8 Python and the
identifier follows from the object's own name:

```python
@model
class MyService:          # → models:blog.my_service
    ...

@model(name="legacy_svc")
class MyService:          # → models:blog.legacy_svc (verbatim)
    ...

@model(name="LegacySvc")
class Other:              # InvalidSegmentError — a stated name must conform
    ...
```

Conversion happens exactly once, when deriving a name from the object.
A derived name that cannot conform even after conversion (a class named
`2Cool`) is still an error — conversion is a convention, not a guess. And
lookup never converts: `resolve("models:blog.MyService")` fails, because
`models:blog.my_service` is the one canonical identifier.

## Registration decorators

The kind set is **closed**, declared once on the framework, and each kind's
decorator comes from `framework.kind()` — there is no add-at-runtime:

```python
import spoc

framework = spoc.Framework("models", "views")

model = framework.kind("models")
view = framework.kind("views")
framework.kind("modle")     # UnknownKindError, lists declared kinds
```

## Registering components

```python
# The name is derived from the object, in snake_case
@view
def list_posts():        # → views:blog.list_posts
    ...

@model
class Post:              # → models:blog.post
    ...

@model
class CommentThread:     # → models:blog.comment_thread
    ...

# Instances have no intrinsic name — an explicit name is always required
model(repo, name="post_repository")
model(repo)   # MissingNameError
```

Identity is never inferred from the execution environment (no stack
inspection). Registration attaches a declaration marker; discovery turns
markers into registry records at `start()`.

Metadata rides along onto the registry record, and its shape is declared by
the kind rather than invented per component:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelMeta:
    table: str
    public: bool = False

framework = spoc.Framework(spoc.KindSpec("models", metadata=ModelMeta))
model = framework.kind("models")

@model(meta=ModelMeta(table="posts", public=True))
class Post:
    ...
```

A kind that declares no `metadata` type accepts no metadata at all, so there
is no untyped channel by default. `ty` proves the field types where they are
written; the kernel checks at registration that the instance matches the kind's
declared type, and a mismatch raises `MetadataContractError`.

## Layout is taxonomy

Discovery happens at framework startup: objects declared in
`<app>/<kind>.py` register under that kind. A mismatch is a **startup
error**, never a silent drop:

```python
# in blog/models.py
@view                             # ComponentKindMismatchError at start:
def list_posts():                 # declared 'views', discovered in 'models'
    ...
```

Objects *imported* into a module register where they are **defined**, not
where they are imported — `from blog.models import post` in another module
does not re-register `post`.

Two objects under the same identifier raise `DuplicateComponentError` at
startup, naming the identifier and the already-registered object.

## The registry record

Each registered component becomes one immutable `Component` record — the
unit of enumeration and projection:

```python
record = framework.resolve("models:blog.post")

record.identifier   # "models:blog.post"
record.kind         # "models"
record.namespace    # "blog"
record.name         # "post"
record.object       # the registered object, unexecuted
record.config       # {"table": "posts"}
record.metadata     # {"public": True, "type": "models"}
```

A surface can build its whole projection — routes, schemas, docs — from
records alone. See [Framework](framework.md) for enumeration and resolution.

## Checking declarations

```python
import spoc

spoc.is_spoc(post)      # carries a SPOC marker?
spoc.get_info(post)     # the Internal marker (name, config, metadata), or None
```
