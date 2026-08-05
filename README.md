# SPOC

<img src="https://raw.githubusercontent.com/hlop3z/spoc/main/docs/docs/assets/images/title.png" alt="title-image" width="100%" />

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Language](https://img.shields.io/github/languages/top/hlop3z/spoc)
![GitHub](https://img.shields.io/github/v/tag/hlop3z/spoc?label=github)
![PyPI](https://img.shields.io/pypi/v/spoc?color=blue)
![Downloads](https://img.shields.io/pypi/dm/spoc?color=darkgreen)

**SPOC** is a registry-first runtime kernel for modular monolithic Python
applications. It sits *below* your HTTP framework — FastAPI, Robyn, anything —
managing internal resources and application objects, and registering every
declared object in one flat registry under a canonical identifier:

```
kind:namespace.object_name        e.g.  models:blog.post
```

Surfaces are built on top by **enumerating the registry**. The kernel
describes; it never executes.

## Features

- **App discovery** — Django-style apps declared by dotted module path and
  imported through the normal import system; the kernel never touches
  `sys.path` and never writes to disk
- **Dependency-ordered loading** — modules initialize in topological order,
  tear down in reverse; sync and async lifecycles (`start`/`astart`), with
  coroutine hooks awaited and refused loudly by the sync path
- **Declarable modes** — the `development` → `staging` → `production` cascade
  is the default, and `[spoc.modes]` extends it (`test = ["test",
  "production"]`) without restating the triple
- **One flat registry** — typed records with `kind` / `namespace` / `name`
  facets; grouped views are derived, never stored
- **Conventional identity** — PEP 8 class names derive their snake_case
  identifier automatically; stated names are verbatim and validated against
  `^[a-z][a-z0-9_]*$`, lookups are always exact, and re-registering an object
  under a different identity raises instead of substituting
- **A stated concurrency contract** — registration is atomic, transitions are
  serialized with one winner, post-boot reads need no coordination
- **Precise resolution** — failures name the failing segment and the valid
  candidates; a typo never falls through to `None`
- **Zero runtime dependencies** — `dependencies = []` is an invariant
- **A shipped test harness** — `spoc.testing` gives every project an isolated
  framework scope, a declarative app-tree builder, and a mode override; with
  pytest installed the same pieces arrive as fixtures automatically, and the
  kernel never imports any of it

Structured-data loading ships in the box as the contained subpackage
`spoc.formats` (`from spoc import formats`) — the kernel never imports it,
importing `spoc` never loads it, and its optional codecs live behind extras
(`pip install "spoc[full]"`).

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

record = framework.resolve("models:blog.post")
print(record.identifier, record.object)

# Project a surface — routes from registry records, nothing else:
routes = [
    (f"/{c.namespace}/{c.object_name}", c.object)
    for c in framework.registry.by_kind("models")
]
```

## Documentation

For detailed documentation, tutorials, and examples:

**[Read the Docs](https://hlop3z.github.io/spoc/)**

## Links

- [PyPI](https://pypi.org/project/spoc)
- [GitHub](https://github.com/hlop3z/spoc)
