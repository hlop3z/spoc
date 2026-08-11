# Name Tags & the Registry

Every block SPOC manages gets exactly **one name tag**, and every tagged block
lives on exactly **one shelf**. This page is about both.

## The name tag: `kind:namespace.object_name`

```
models : blog . post
  │       │      │
  kind    │      the block's own name
          the app it lives in
```

Three segments, always in that order, each one lowercase snake_case
(`^[a-z][a-z0-9_]*$`). Some examples:

| You write                              | The tag says                 |
| -------------------------------------- | ---------------------------- |
| `class Post` in `apps/blog/models.py`  | `models:blog.post`           |
| `class HTTPServer` in `apps/web/views.py` | `views:web.http_server`   |
| `@models(name="admin")` in `apps/blog` | `models:blog.admin`          |

Two rules make names predictable:

- A name SPOC **derives** from your class or function is converted to
  snake_case first (`UserAccount` → `user_account`).
- A name you **state** with `name=` is used verbatim — and if it breaks the
  grammar, you get an error instead of a silent rewrite.

You can work with tags in code, too:

```python
import spoc

tag = spoc.parse("models:blog.post")
print(tag.kind)
#> models
print(tag.namespace)
#> blog
print(tag.object_name)
#> post

print(spoc.compose("models", "blog", "post"))
#> models:blog.post
```

## The shelf: one registry, many views

After `start()`, every block is a `Component` record in
`framework.registry` — one flat, ordered collection. The examples on this
page run against the smallest possible project:

```python title="framework.py"
import spoc

framework = spoc.Framework("models")

models = framework.kind("models")
```

```python title="apps/blog/models.py"
from framework import models


@models
class Post: ...
```

```toml title="config/spoc.toml"
[spoc.apps]
development = ["apps.blog"]
```

Boot it and ask the shelf anything:

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent
framework.start(BASE_DIR)

len(framework.registry)                    # how many blocks
"models:blog.post" in framework.registry   # True

for component in framework.registry:       # everything, in tag order
    print(component.identifier)

framework.registry.by_kind("models")       # just the models
framework.registry.by_namespace("blog")    # just the blog app's blocks
framework.registry.namespaces()            # ('blog', ...)
```

Each record carries the tag, its three segments, the block itself, and any
metadata:

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent
framework.start(BASE_DIR)

record = framework.resolve("models:blog.post")
record.identifier    # "models:blog.post"
record.kind          # "models"
record.namespace     # "blog"
record.object_name   # "post"
record.object        # <class 'apps.blog.models.Post'>
record.metadata      # whatever the block handed in, or None
```

This one collection is the whole point: a web app, a CLI, an admin panel —
each is just a loop over the registry, projecting records into routes or
commands. No second list to keep in sync.

## Mistakes fail loudly (and precisely)

Ask for a tag that isn't there and SPOC tells you **which segment** failed and
what would have matched:

```python title="main.py"
from pathlib import Path

import spoc

from framework import framework

BASE_DIR = Path(__file__).resolve().parent
framework.start(BASE_DIR)

try:
    framework.resolve("models:blog.pots")
except spoc.UnknownObjectError as error:
    print(error)
    # UnknownObjectError: Unknown object_name 'pots' in models:blog. Registered: post
```

The same honesty applies when blocks go *onto* the shelf:

- Two different blocks claiming the same tag → refused (`DuplicateComponentError`).
- One block claiming two different tags → refused (`IdentityDivergenceError`).
- The same block, same tag, twice → fine; nothing to do.

A typo is never quietly skipped — the shelf either has exactly what your apps
declared, or the boot tells you why not.

Next: [apps & modes](apps.md).
