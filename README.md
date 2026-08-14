# SPOC

<img src="https://raw.githubusercontent.com/hlop3z/spoc/main/docs/docs/assets/images/title.png" alt="title-image" width="100%" />

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Language](https://img.shields.io/github/languages/top/hlop3z/spoc)
![GitHub](https://img.shields.io/github/v/tag/hlop3z/spoc?label=github)
![PyPI](https://img.shields.io/pypi/v/spoc?color=blue)
![Downloads](https://img.shields.io/pypi/dm/spoc?color=darkgreen)

**Every framework has a part that finds your code.** Django finds `models.py`.
pytest finds `test_*`. FastAPI collects the functions you decorated. Each of them
built the same machinery from scratch: a naming rule, a discovery pass, a registry,
a boot order.

**SPOC is that machinery on its own** — so you can point it at *your* kinds of thing.
You name the kinds; SPOC gives you the decorators, the discovery, the registry, the
lifecycle, the CLI, the autocomplete, and the test fixtures.

Every component lands on one shelf under one name:

```
kind:namespace.object_name        e.g.  models:blog.post
```

That name is the whole interface. SPOC describes what your app contains. It never
runs it.

## See it work

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

**Nobody wrote that command list.** It was derived from what the app registered. Add
a function to `apps/core/commands.py` and it becomes a subcommand; delete it and it
leaves. The CLI file never changes.

That's the whole trade: name your components once, and every surface reads them for
free.

## What SPOC decides — and what stays yours

| SPOC decides                                   | You decide                                      |
| ---------------------------------------------- | ----------------------------------------------- |
| that the kinds are declared once, in one place  | what the kinds are — `models`, `jobs`, anything |
| that every component has exactly one name       | what your components are and do                 |
| that a folder is a namespace, a filename a kind | where those folders live                        |
| which apps boot, and in what order              | what start and stop *mean* for your resources   |
| how the registry is read, typed, and tested     | every surface that reads it                     |

**SPOC never runs your components.** That is what keeps it *underneath* your stack
instead of competing with it. FastAPI still serves your HTTP. Typer still parses your
argv. Celery still runs your jobs. pytest still runs your tests. SPOC answers the one
question none of them answer: *what does this app contain, and under what name?*

## "Why not just…?"

None of these are competitors. The question is only which one owns your structure.

| You could use…   | Which is right until…                                                                                       |
| ---------------- | ----------------------------------------------------------------------------------------------------------- |
| **imports**      | you need *every* thing of a kind at runtime — then someone hand-maintains a list, and it drifts.              |
| **entry points** | you notice they are for installed distributions: flat, unordered, no lifecycle. In-repo packages have none.   |
| **pluggy**       | you see it solves the other half: pluggy *calls* hooks you specified, SPOC *names* objects you invented.      |
| **Django**       | you want the registry without the ORM, the settings system, and an opinion about your transport.              |
| **a container**  | you find DI answers "how is this built", not "what exists, under what name, in what boot order".              |

## Should you use it?

**Yes, if…**

- one codebase feeds several surfaces — HTTP *and* CLI *and* workers — and each
  re-discovers the same components its own way.
- you are shipping a framework other people write apps against.
- things must start in dependency order and stop in reverse.
- a mistyped component name should be an editor error, not a `None` at 3am.

**No, if…**

- it's one app, one surface, a handful of modules. Imports are cheaper. SPOC pays off
  above a complexity threshold, not below it.
- you are already on Django. Its app registry *is* a structural model.
- you want something that *runs* your components. SPOC only names and orders them.

## Quick Start

Four small files — that's the whole thing.

**Your rules.** Which kinds exist, declared once:

```python title="framework.py"
# framework.py
import spoc

framework = spoc.Framework("models")   # the kinds
model = framework.kind("models")       # a ready-made decorator
```

**Your app.** The folder is the namespace, the filename is the kind:

```python title="apps/blog/models.py"
# apps/blog/models.py
from framework import model


@model
class Post:
    """Registers as models:blog.post — the name is derived, not typed out."""
```

**Your settings.** Which apps boot:

```toml title="config/spoc.toml"
# config/spoc.toml
[spoc.apps]
development = ["apps.blog"]
```

**Your entry point.** Start, then read the shelf:

```python title="main.py"
# main.py
from pathlib import Path

from framework import framework

framework.start(Path(__file__).resolve().parent)  # nothing happens until this

# By name, or by path — the same record either way.
post = framework.resolve("models:blog.post")
post = framework.objects.models.blog.post

# A surface is a loop over the shelf. Here, URLs:
for c in framework.registry.by_kind("models"):
    print(f"/{c.namespace}/{c.object_name}", c.object)
```

Prefer to start from a generated project? `uvx spoc init myproject` scaffolds one
without installing anything.

## What you get

- **One name per component, always.** Class names derive their own. Ask for a name
  that isn't there and the error says *which segment* was wrong and what would have
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

## What you build on top

```
                          your apps
                 (models, views, jobs, …)
                              │  @decorators
                              ▼
                   ┌─────────────────────┐
                   │    SPOC registry    │   kind:namespace.object_name
                   └─────────────────────┘
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         HTTP surface     CLI surface    worker surface
         (FastAPI, …)     (Typer, …)     (Celery, …)
```

Each surface is a loop over `registry.by_kind(...)` — written once, and every app you
add later flows through it. [Build a
framework](https://hlop3z.github.io/spoc/learn/build-a-framework/) takes an empty
folder to `curl` talking to an HTTP framework *you* wrote, in four files, with nothing
installed but `spoc`.

## Install

**Python 3.12+**

```bash
pip install spoc
```

Scaffolding needs no install at all: `uvx spoc init myproject` generates a project
without touching your environment. The generated project imports `spoc` at runtime, so
install it where you run the project from —
[installation guide](https://hlop3z.github.io/spoc/getting-started/installation/).

## Documentation

**[Read the docs](https://hlop3z.github.io/spoc/)** — tutorials, how-to guides, and the
full API reference.

A good path in: [your first project](https://hlop3z.github.io/spoc/getting-started/quick-start/)
→ [names & the registry](https://hlop3z.github.io/spoc/learn/names-and-registry/)
→ [build a framework](https://hlop3z.github.io/spoc/learn/build-a-framework/).

## Stability

SPOC is 1.0. A `public` name changes incompatibly only in a major release, and only
after a completed deprecation cycle — so `spoc>=1.0,<2` is the pin that matters. Every
name, command, and extra carries a tier (`public`, `provisional`, `internal`), and both
the tiers and every change to them are checked on each CI run.

**[Stability & Versioning](https://hlop3z.github.io/spoc/api/stability/)** — the tiers,
the deprecation lifecycle, and the criteria 1.0 was cut against.

## Links

- [PyPI](https://pypi.org/project/spoc)
- [GitHub](https://github.com/hlop3z/spoc)
