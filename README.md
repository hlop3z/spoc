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

- **App discovery** — Django-style apps, selected per mode
  (`development` → `staging` → `production` cascade) via `spoc.toml`
- **Dependency-ordered loading** — modules initialize in topological order,
  tear down in reverse
- **One flat registry** — typed records with `kind` / `namespace` / `name`
  facets; grouped views are derived, never stored
- **Conventional identity** — PEP 8 class names derive their snake_case
  identifier automatically; stated names are verbatim and validated against
  `^[a-z][a-z0-9_]*$`, and lookups are always exact
- **Precise resolution** — failures name the failing segment and the valid
  candidates; a typo never falls through to `None`
- **Zero runtime dependencies** — `dependencies = []` is an invariant

## Installation

**Requires Python 3.13+**

```bash
pip install spoc
```

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

record = framework.resolve("models:blog.post")
print(record.identifier, record.object)

# Project a surface — routes from registry records, nothing else:
routes = [
    (f"/{c.namespace}/{c.name}", c.object)
    for c in framework.registry.by_kind("models")
]
```

## Documentation

For detailed documentation, tutorials, and examples:

**[Read the Docs](https://hlop3z.github.io/spoc/)**

## Links

- [PyPI](https://pypi.org/project/spoc)
- [GitHub](https://github.com/hlop3z/spoc)
