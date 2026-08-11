# Add a Database

**How do I open a database pool once at boot, share it everywhere, and close
it on the way out?** Declare it as a `resources` component — the one kind in
[the default vocabulary](../learn/vocabulary.md) with lifecycle hooks. No
untyped `app.state` bag: the pool lives on the registry like everything else.

This page is a complete, runnable project.

## 1. Declare the kind, with hooks

```python title="framework.py"
import spoc


def _open(resources):
    for resource in resources:
        resource.open()


def _close(resources):
    for resource in resources:
        resource.close()


framework = spoc.Framework(
    "views",
    spoc.KindSpec("resources", on_startup=_open, on_shutdown=_close),
)

view = framework.kind("views")
resource = framework.kind("resources")
```

## 2. Declare the resource — an instance that opens and closes itself

Instances have no `__name__`, so name it explicitly:

```python title="apps/core/resources.py"
from framework import resource


class Database:
    """A stand-in for your engine/pool of choice."""

    def __init__(self):
        self.pool = None

    def open(self):
        self.pool = {"connected": True}   # real code: create the pool here

    def close(self):
        self.pool = None


database = resource(Database(), name="database")   # → resources:core.database
```

## 3. Reach it through the registry, at call time

```python title="apps/core/views.py"
from framework import framework, view


@view
def health():
    db = framework.resolve("resources:core.database").object
    return {"database": "up" if db.pool else "down"}
```

## 4. Boot and see the whole loop

```toml title="config/spoc.toml"
[spoc.apps]
development = ["apps.core"]
```

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent

framework.start(BASE_DIR)

health = framework.resolve("views:core.health").object
print(health())   # {'database': 'up'}

framework.shutdown()
```

On `start()`, the kind's `on_startup` opens every declared resource before
your surface takes traffic; on `shutdown()`, `on_shutdown` closes them in
reverse module order. After teardown, resolving `resources:core.database`
fails with a named error — you can never be handed a dead pool.

The whys and the fine points — resolve-at-call-time, `depends_on` ordering,
the async twin — are on [The Default Vocabulary](../learn/vocabulary.md).

Next: [bind a transport](bind-a-transport.md).
