# The Framework Object

`spoc.Framework` is where you write your rules. Everything SPOC knows about
your framework is stated **once**, on this one object.

```python
import spoc

framework = spoc.Framework("models", "views")
```

Creating it does nothing else — no files are read, no modules imported.
Your project only boots when you call `start()`.

## Kinds: the types of blocks

A **kind** is a category of building block. A plain string declares a simple
kind. When a kind needs more — an order, a rule, a hook — use a
`spoc.KindSpec`:

```python
import spoc

framework = spoc.Framework(
    "models",
    spoc.KindSpec("views", depends_on=("models",)),   # views load after models
    spoc.KindSpec("middleware", required=False),      # apps may skip this one
)
```

Everything a kind can say, on one record:

| Field         | Default | Meaning                                                        |
| ------------- | ------- | -------------------------------------------------------------- |
| `name`        | —       | The kind's name (lowercase snake_case)                         |
| `depends_on`  | `()`    | Kinds whose modules must load before this one's                |
| `required`    | `True`  | Must every app provide a module for this kind?                 |
| `metadata`    | `None`  | A class every block of this kind must carry as metadata        |
| `on_startup`  | `None`  | Called with each app's blocks of this kind at boot             |
| `on_shutdown` | `None`  | Called the same way at shutdown                                |

Declaring the same kind twice is refused — one declaration, no drift.

## Decorators: putting name tags on blocks

`framework.kind("models")` hands you the decorator for that kind. Apps import
it and mark their blocks:

```python
import spoc

framework = spoc.Framework("models")
model = framework.kind("models")


@model
class UserAccount:          # → models:<app>.user_account
    ...


@model(name="admin")       # state the name yourself instead
class Whatever:             # → models:<app>.admin
    ...
```

Inside an app you'd write `from framework import model` instead of the four
setup lines — the decorator is the same object either way. The kind is plural
(`models` is a category); the decorator is singular, because it marks one
thing. `spoc init` names them that way for you — and where the singular is a
word Python reserves, it adds the trailing underscore PEP 8 uses for exactly
that (`spoc init shop --kinds class` gives you `class_`). The kind keeps the
name you declared; only the variable is spelled around the language.

A derived name is converted for you: `UserAccount` → `user_account`,
`HTTPServer` → `http_server`. A name you *state* is used exactly as written —
never silently rewritten. Blocks can be classes, functions, or objects.

## Metadata: a form every block must fill in

If a kind declares a `metadata` class, every block of that kind must hand in
an instance — and blocks of other kinds must not:

```python
import dataclasses as dc

import spoc


@dc.dataclass
class Route:
    path: str


framework = spoc.Framework(spoc.KindSpec("views", metadata=Route))
view = framework.kind("views")


@view(meta=Route(path="/posts"))
def list_posts():
    ...
```

The form comes back on the record: `framework.resolve("views:blog.list_posts").metadata.path`.

## Start, ask, stop

```python test="skip"
framework.start(BASE_DIR)        # boot: read settings, import apps, fill the shelf
framework.started                # True

record = framework.resolve("models:blog.user_account")
record.object                    # the class itself, unchanged

framework.shutdown()             # tear down in reverse, back to square one
```

`resolve` is a pure lookup — SPOC hands the block back and never calls it.
Running things is your job, in the layers you build on top.

There's also an async pair, `astart`/`ashutdown` — see
[Start & Stop](lifecycle.md).

## One more hook: `on_ready`

Want to run something once, after every block is on the shelf but before the
project is live? Register a ready callback:

```python
import spoc

framework = spoc.Framework("models")


@framework.on_ready
def announce(registry):
    print(f"Ready: {len(registry)} components registered")
```

Next: [name tags and the registry](names-and-registry.md).
