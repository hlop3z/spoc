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
- **Validated identity** — every segment must be lowercase snake_case,
  checked at registration; SPOC **rejects, never normalizes**
- **Precise resolution** — `framework.resolve("models:blog.post")` fails per
  segment, naming what didn't resolve and the valid candidates
- **Lifecycle hooks** — startup and shutdown per module pattern
- **TOML configuration** — `spoc.toml` + settings + per-mode environments

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
from spoc import Components, Framework, Schema

components = Components("models")

@components.register("models")
class post:
    ...

framework = Framework(
    base_dir=Path(__file__).parent,
    schema=Schema(modules=["models"]),
)

record = framework.resolve("models:blog.post")   # a Component record
for component in framework.registry:              # deterministic enumeration
    print(component.identifier)
```

Continue with the [Quick Start](getting-started/quick-start.md).
