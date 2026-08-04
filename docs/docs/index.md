# SPOC

**A registry-first runtime kernel for modular monolithic Python applications.**

SPOC sits *below* your HTTP framework, not in place of it. It discovers apps,
loads their modules in dependency order, manages lifecycle, and registers
every declared object in one flat registry under a canonical identifier:

```
kind:namespace.object_name        e.g.  models:blog.post
```

Surfaces — FastAPI, Robyn, a CLI, a worker — are built *on top* by
enumerating the registry. The kernel **describes; it never executes**: it
never calls your code beyond lifecycle hooks, and resolution is a pure
lookup.

## What SPOC does

- **App discovery** — Django-style apps in an `apps/` directory, selected per
  mode (`development` → `staging` → `production` cascade) via `spoc.toml`
- **Dependency-ordered loading** — modules load and initialize in topological
  order; teardown runs in reverse
- **One flat registry** — every component is a typed record with `kind`,
  `namespace`, and `name` facets; grouped views are derived, never stored
- **Conventional identity** — write PEP 8 Python; class names derive their
  snake_case identifier automatically. A name you *state* is verbatim and
  validated, and lookups are always exact
- **Precise resolution** — `framework.resolve("models:blog.post")` fails per
  segment, naming what didn't resolve and the valid candidates
- **Lifecycle phases** — `on_ready` finalize after discovery, per-kind
  startup/shutdown hooks, module `initialize`/`teardown`
- **One config file** — `spoc.toml` is the only file the kernel reads;
  your `settings.py` stays yours

## What SPOC deliberately does not do

- **No dependency injection** — resolution is a lookup; wiring belongs to
  consumers (adopt a DI container on top if you want one)
- **No invocation** — there is no `do()`; identifiers have exactly three
  segments and never an operation suffix
- **No event bus, no HTTP, no workers** — those are apps and surfaces that
  register *on* the kernel

## Zero dependencies

The kernel has no runtime dependencies — `dependencies = []` is an invariant,
not an accident.

## A taste

```python
from pathlib import Path
import spoc

framework = spoc.Framework("models")
model = framework.kind("models")

@model
class Post:                                # → models:blog.post
    ...

framework.start(Path(__file__).parent)

record = framework.resolve("models:blog.post")   # a Component record
for component in framework.registry:              # deterministic enumeration
    print(component.identifier)
```

Continue with the [Quick Start](getting-started/quick-start.md).
