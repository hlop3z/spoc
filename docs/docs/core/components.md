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

Every segment must match `^[a-z][a-z0-9_]*$` (lowercase snake_case),
validated at registration. There are exactly three segments — an operation
suffix is malformed by design.

**Validation rejects; it never normalizes.** A class named `MyService` is a
registration error, not a silent rename:

```python
@components.register("models")
class MyService:          # InvalidSegmentError: invalid object_name 'MyService'
    ...

@components.register("models", name="my_service")
class MyService:          # OK — explicit, conforming name
    ...
```

## Declaring a kind set

The kind set is **closed** and fixed at construction — there is no
add-at-runtime:

```python
from spoc import Components

components = Components("models", "views")   # must match Schema.modules
components.register("modle", name="x")       # UnknownKindError, lists declared kinds
```

## Registering components

```python
# Classes and functions: name defaults from __name__ when it conforms
@components.register("models")
class post:
    ...

@components.register("views")
def list_posts():
    ...

# Explicit name (required when __name__ doesn't conform)
@components.register("models", name="comment_thread")
class CommentThread:
    ...

# Instances have no intrinsic name — an explicit name is always required
components.register("models", repo, name="post_repository")
components.register("models", repo)   # MissingNameError
```

Identity is never inferred from the execution environment (no stack
inspection) and registration never mutates the object being registered.

`config` and `metadata` ride along onto the registry record:

```python
@components.register("models", config={"table": "posts"}, metadata={"public": True})
class post:
    ...
```

## Layout is taxonomy

Discovery happens at framework startup: objects declared in
`<app>/<kind>.py` register under that kind. A mismatch is a **startup
error**, never a silent drop:

```python
# in blog/models.py
@components.register("views")     # ComponentKindMismatchError at startup:
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
components.is_spoc(post)                  # carries a SPOC marker?
components.is_component("models", post)   # declared under this kind?
components.get_info(post)                 # the Internal marker, or None
```
