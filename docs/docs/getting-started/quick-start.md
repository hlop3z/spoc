# Your First Project

Two minutes, three commands, and you'll have a running framework.

## 1. Generate a project

```bash
spoc init hello
cd hello
```

This generates the _default_ template — the smallest project that runs, which
is the right one to learn from. The README's demo used
`spoc init myproject --template starter`, a fuller project with working CLI
commands; that one is walked through in [The Starter](starter.md).

`spoc init` creates a small project that runs **without editing anything**:

```
hello/
├── config/
│   └── spoc.toml        # your settings — the only file SPOC reads
├── apps/
│   └── core/            # your first app
│       ├── __init__.py
│       ├── models.py    # blocks of kind "models"
│       └── views.py     # blocks of kind "views"
├── framework.py         # your rules: which kinds exist
└── main.py              # the entry point
```

## 2. Run it

```bash
python main.py
```

```text
Ready: 2 components registered
Installed apps: ['apps.core']
 - models:core.example
 - views:core.example
```

That's SPOC booting: it read your settings, imported your app, found two
blocks, and put them on the shelf with their name tags.

Note the program says _components_ where this page says _blocks_ — those are
one thing. **`Component`** is the API's name for a record on the shelf; _block_
is the word these guides use while you're learning. From here on you'll see
both.

## 3. Read the three files

**`framework.py` — your rules.** One declaration says which kinds of blocks
exist. One decorator per kind is handed to your apps:

```python title="framework.py"
"""The entire framework definition for hello: one declaration."""

import spoc

framework = spoc.Framework("models", "views")

# One decorator per declared kind. Apps import these to declare components.
model = framework.kind("models")
view = framework.kind("views")
```

**`apps/core/models.py` — a block.** The decorator puts a name tag on the
class. `Example` in app `core` of kind `models` becomes
`models:core.example` — you never write that string yourself:

```python title="apps/core/models.py"
from framework import model


@model
class Example:
    """Registers as models:core.example."""
```

`apps/core/views.py` is the same shape for the `views` kind:

```python title="apps/core/views.py"
from framework import view


@view
class Example:
    """Registers as views:core.example."""
```

**`main.py` — the start button.** Nothing happens until you press it:

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    framework.start(BASE_DIR)

    for component in framework.registry:
        print(" -", component.identifier)

    framework.shutdown()
```

## 4. Add a second app

```bash
spoc app blog
```

SPOC reads your `framework.py`, sees the kinds are `models` and `views`, and
generates `apps/blog/` with one module per kind. It never edits your settings
— it prints the exact line to add. Open `config/spoc.toml` and install it:

```toml title="config/spoc.toml"
[spoc.apps]
production = ["apps.core"]
staging = []
development = ["apps.blog"]
```

Now give the blog a real block:

```python title="apps/blog/models.py"
from framework import model


@model
class Post:
    """Registers as models:blog.post."""
```

The generated `apps/blog/views.py` keeps its starter block — that's the
`views:blog.example` you're about to see on the shelf:

```python title="apps/blog/views.py"
from framework import view


@view
class Example:
    """Registers as views:blog.example."""
```

## 5. Ask the shelf

```bash
spoc list
```

```text
models:blog.post
models:core.example
views:blog.example
views:core.example
```

And from Python, `resolve` turns a name tag back into the block. Update
`main.py` to ask for the post:

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    framework.start(BASE_DIR)

    record = framework.resolve("models:blog.post")
    print(record.object)     # <class 'apps.blog.models.Post'>
    print(record.kind)       # models
    print(record.namespace)  # blog

    framework.shutdown()
```

## You now know the loop

Declare kinds → write apps → `start()` → resolve from the registry. Everything
else in these docs is detail on one of those four steps.

Next: [the settings file](configuration.md), or jump to
[how the framework object works](../learn/framework.md).
