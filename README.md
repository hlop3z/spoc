# SPOC

<img src="https://raw.githubusercontent.com/hlop3z/spoc/main/docs/docs/assets/images/title.png" alt="title-image" width="100%" />

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Language](https://img.shields.io/github/languages/top/hlop3z/spoc)
![GitHub](https://img.shields.io/github/v/tag/hlop3z/spoc?label=github)
![PyPI](https://img.shields.io/pypi/v/spoc?color=blue)
![Downloads](https://img.shields.io/pypi/dm/spoc?color=darkgreen)

## Build a framework in 30 lines

Say what kinds of things your app has:

```python title="framework.py"
import spoc

framework = spoc.Framework("models", "commands", "views")

model = framework.kind("models")
command = framework.kind("commands")
view = framework.kind("views")
```

Tag your code with them, anywhere in the project:

```python title="apps/blog/models.py"
from framework import model


@model
class Post:
    """Registers as models:blog.post."""
```

```python title="apps/blog/commands.py"
from framework import command


@command
def publish(title: str = "Hello, SPOC") -> str:
    """Registers as commands:blog.publish."""
    return f"published {title!r}"
```

```python title="apps/blog/views.py"
from framework import view


@view
def posts_api() -> list[str]:
    """Registers as views:blog.posts_api."""
    return []
```

```toml title="config/spoc.toml"
[spoc.apps]
development = ["apps.blog"]
```

```python title="main.py"
from pathlib import Path

from framework import framework

framework.start(Path(__file__).resolve().parent)
```

That's it — no registry to wire up, no list to keep in sync. Ask SPOC what it found:

```bash
spoc check
spoc list
spoc stubs
```

```text
OK: /path/to/blog checks out clean
commands:blog.publish
models:blog.post
views:blog.posts_api
wrote framework.pyi (3 identifiers)
```

**SPOC turns your application's declarations into one typed, inspectable registry.**

`check` dry-boots your project and reports what's wrong before anything runs.
`list` reads the shelf. `stubs` writes real autocomplete for every name you just
typed — so `framework.objects.models.blog.post` completes in your editor before
you've written a single test. Add a fourth decorated function tomorrow; all three
commands see it with no edit to any of these files.

## See it work without writing a file

```bash
pip install spoc
spoc init myproject --template starter
cd myproject && python main.py --help
```

```
usage: myproject [-h] {core.add,core.items} ...

positional arguments:
  {core.add,core.items}
    core.add            Add an item to the store.
    core.items          List the items in the store.

options:
  -h, --help            show this help message and exit
```

**Nobody wrote that command list.** It was derived from what the generated app
registered — the same trick as above, scaffolded for you. `uvx spoc init myproject`
works with nothing installed at all.

## What you get

- **One name per component, always.** Class names derive their own. Ask for a name
  that isn't there and the error says _which segment_ was wrong and what would have
  matched — never a silent `None`.
- **Autocomplete, with no code changes.** `spoc stubs` writes a type stub beside your
  entry point: names complete as you type, components come back as their real types,
  typos become editor errors. `spoc projection` emits the same registry as JSON for
  tools in any language.
- **A lifecycle you can reason about.** Modules start in dependency order and stop in
  reverse, sync or async.
- **Problems found before runtime.** `spoc check` dry-boots and reports config errors,
  cycles, collisions, and sync/async mismatches. `spoc list` and `spoc explain` read
  the registry from your terminal.
- **Tests in the box.** `spoc.testing` gives isolated framework scopes and an app-tree
  builder, arriving as ready-made pytest fixtures.
- **Zero dependencies.** `dependencies = []`, enforced. Optional data-format codecs
  live behind extras (`pip install "spoc[full]"`).

**SPOC never runs your components.** FastAPI still serves your HTTP, Typer still
parses your argv, Celery still runs your jobs. SPOC only answers _what does this
app contain, and under what name_ — how [architecture, names, and lifecycle work
underneath](https://hlop3z.github.io/spoc/learn/framework/) is in the docs.

## Should you use it?

**Yes, if…**

- one codebase feeds several surfaces — HTTP _and_ CLI _and_ workers — and each
  re-discovers the same components its own way.
- you are shipping a framework other people write apps against.
- things must start in dependency order and stop in reverse.
- a mistyped component name should be an editor error, not a `None` at 3am.

**No, if…**

- it's one app, one surface, a handful of modules. Imports are cheaper. SPOC pays off
  above a complexity threshold, not below it.
- you are already on Django. Its app registry _is_ a structural model.
- you want something that _runs_ your components. SPOC only names and orders them.

Weighing it against imports, entry points, pluggy, or a DI container specifically?
[Why not just…?](https://hlop3z.github.io/spoc/#why-not-just) has the one-line answer
for each.

## Install

**Python 3.12+**

```bash
pip install spoc
```

The generated project imports `spoc` at runtime, so install it where you run the
project from — [installation guide](https://hlop3z.github.io/spoc/getting-started/installation/).

## Documentation

**[Read the docs](https://hlop3z.github.io/spoc/)** — tutorials, how-to guides, and the
full API reference.

A good path in: [your first project](https://hlop3z.github.io/spoc/getting-started/quick-start/)
→ [names & the registry](https://hlop3z.github.io/spoc/learn/names-and-registry/)
→ [build a framework](https://hlop3z.github.io/spoc/learn/build-a-framework/).

## Links

- [PyPI](https://pypi.org/project/spoc)
- [GitHub](https://github.com/hlop3z/spoc)
