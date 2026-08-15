# Plugins

Most blocks live in apps and wear a decorator. **Plugins** are a second way to
put blocks on the shelf: name them in `spoc.toml`, and SPOC imports and
registers them at boot. Same shelf, same name tags — just declared in
settings instead of code.

This is handy for things that come from outside your apps: a middleware from a
library, a hook you want swappable per deployment.

## Declaring one

Each group under `[spoc.plugins]` names a **declared kind**; each entry is a
dotted reference `module.attribute`:

```python title="framework.py"
import spoc

framework = spoc.Framework(
    "models",
    spoc.KindSpec("middleware", required=False),  # only settings populate it
)
```

```toml title="config/spoc.toml"
[spoc.plugins]
middleware = ["extras.middleware"]
```

```python title="extras.py"
def middleware():
    print("hello from middleware")
```

At boot, `extras.middleware` registers as `middleware:extras.middleware` and
resolves like any other block:

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent

framework.start(BASE_DIR)

middleware = framework.resolve("middleware:extras.middleware").object
middleware()   # hello from middleware

framework.shutdown()
```

## How the tag is made

A reference reads `<package>.<module>.<attribute>`:

- The segment **before the module** is the namespace — for a top-level module
  like `extras`, the module is its own namespace.
- The **attribute** becomes the object name (converted to snake_case).

So `apps.demo.extras.hook` would register as `hooks:demo.hook`.

## The fine print

- **The group must be a declared kind.** A typo like `middlewear` fails the
  boot, naming the valid kinds.
- **Mark plugin-only kinds `required=False`** — otherwise every app must ship
  a module file for them.
- **Kinds with a `metadata` contract can't be populated this way.** A name in
  a settings file has nowhere to carry the metadata, and SPOC says exactly
  that instead of reporting a contract violation you couldn't fix.
- **Kind hooks don't fire for plugin-only kinds.** `on_startup`/`on_shutdown`
  fire per app _module_, and a plugin has none.

Next: [build a framework](build-a-framework.md) — everything on these pages,
in four files you author.
