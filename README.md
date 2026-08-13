# SPOC

<img src="https://raw.githubusercontent.com/hlop3z/spoc/main/docs/docs/assets/images/title.png" alt="title-image" width="100%" />

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Language](https://img.shields.io/github/languages/top/hlop3z/spoc)
![GitHub](https://img.shields.io/github/v/tag/hlop3z/spoc?label=github)
![PyPI](https://img.shields.io/pypi/v/spoc?color=blue)
![Downloads](https://img.shields.io/pypi/dm/spoc?color=darkgreen)

**SPOC is a kit for building your own framework.** You declare the kinds of thing
your framework has; SPOC gives you the decorators, the discovery, the lifecycle,
the CLI, and the test fixtures derived from that one declaration.

Everything your apps declare lands in one flat registry under a canonical name:

```
kind:namespace.object_name        e.g.  models:blog.post
```

That name is the whole interface. Your surfaces — routes, commands, admin pages —
are loops over the registry. SPOC describes what exists; it never executes it.

## What you get

- **One grammar, everywhere.** Every component has exactly one canonical name.
  PEP 8 class names derive their own; stated names are used verbatim and
  validated. Ask for a name that isn't there and the failure says *which segment*
  was wrong and what would have matched — never a silent `None`.
- **Two ways to reach a component.** `resolve("models:blog.post")` for names built
  at runtime, or `objects.models.blog.post` for names you know as you type —
  the second completes segment by segment in your editor.
- **Editor autocomplete with no code changes.** `spoc stubs` writes a type stub
  beside your composition root: identifiers complete as you type, components come
  back as their real types, and typos become editor errors. `spoc projection`
  emits the same registry as JSON with a published schema, for tools in any
  language.
- **A lifecycle you can reason about.** Modules initialize in dependency order and
  tear down in reverse, sync or async. Registration is atomic, transitions are
  serialized with exactly one winner, and post-boot reads need no coordination —
  written down as a contract, not left to discover.
- **Problems found before runtime.** `spoc check` dry-boots the project and
  reports config errors, unresolvable apps, cycles, collisions, and sync/async
  mismatches. `spoc list` and `spoc explain` read the registry from your terminal.
- **A test harness in the box.** `spoc.testing` gives isolated framework scopes, a
  declarative app-tree builder, and mode overrides — arriving as ready-made test
  fixtures, without the kernel importing any of it.
- **Zero runtime dependencies.** `dependencies = []` is an enforced invariant.
  Data-format loading ships as the contained `spoc.formats` subpackage, whose
  optional codecs live behind extras (`pip install "spoc[full]"`).

## Installation

**Requires Python 3.12+**

```bash
pip install spoc
```

Scaffolding a project needs no install at all — `spoc init` ships as a console script,
and SPOC has no dependencies to resolve:

```bash
uvx spoc init myproject      # generate; installs nothing
```

The generated project imports `spoc` at runtime, so install it in the environment you
run the project from. Full detail in the
[installation guide](https://hlop3z.github.io/spoc/getting-started/installation/).

## Quick Start

```python
from pathlib import Path
import spoc

framework = spoc.Framework("models")       # the closed kind set, declared once
model = framework.kind("models")           # a ready-made decorator

@model
class Post:                                # apps/blog/models.py → models:blog.post
    ...

framework.start(Path(__file__).parent)     # construction is inert; start boots
# async surfaces: await framework.astart(...) awaits coroutine hooks

# By name, or by path — the identical record either way.
record = framework.resolve("models:blog.post")
record = framework.objects.models.blog.post

# Project a surface — routes from registry records, nothing else:
routes = [
    (f"/{c.namespace}/{c.object_name}", c.object)
    for c in framework.registry.by_kind("models")
]
```

Start a project with no install at all:

```bash
uvx spoc init myproject
```

## Documentation

**[Read the docs](https://hlop3z.github.io/spoc/)** — tutorials, how-to guides, and
the full API reference.

A good path in: [your first project](https://hlop3z.github.io/spoc/getting-started/quick-start/)
→ [name tags & the registry](https://hlop3z.github.io/spoc/learn/names-and-registry/)
→ [build a framework](https://hlop3z.github.io/spoc/learn/build-a-framework/).

## Stability

SPOC is 1.0. Every name, command, and extra carries one of three tiers —
`public`, `provisional`, or `internal`. For an importable name the tier follows from
how it is exposed: exported from a package is `public`, saying so in its own docstring
makes it `provisional`, and reachable only through a submodule is `internal`. Both the
tiers and every change to them since the last release are checked on every CI run.
A `public` element now changes incompatibly only in a major release, and only after a
completed deprecation lifecycle, so `spoc>=1.0,<2` is the pin that matters.

**[Stability & Versioning](https://hlop3z.github.io/spoc/api/stability/)** — the
tiers, what they exclude, the deprecation lifecycle, and the criteria 1.0 was cut
against.

## Links

- [PyPI](https://pypi.org/project/spoc)
- [GitHub](https://github.com/hlop3z/spoc)
