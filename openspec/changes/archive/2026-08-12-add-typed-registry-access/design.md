## Context

`Component.object` is `Any`. Every consumption site therefore loses the type it just looked
up. From `examples/apps/orders/views.py`:

```python
# orders never imports catalog — that decoupling IS the registry's purpose
product_cls = framework.resolve("models:catalog.product").object   # Any
stock = framework.resolve("views:catalog.list_products").object()  # Any
```

The editor completes nothing on `product_cls`, and `"models:catalog.prodcut"` is a runtime
error. The constraint that rules out the obvious fixes is stated in that file's own comment:
`orders` must not import `catalog`. So:

| Candidate | Why it fails here |
| --- | --- |
| `resolve(id) -> T` + caller annotation | Restates a type the registry already knows |
| `resolve(id, Product) -> Product` | Requires importing `catalog` — deletes the decoupling |
| `get(Product) -> Product` | Container semantics: assumes one instance per type. The registry holds *many* components per kind, and holds the class itself, not an instance |

Three facts about the existing system decide the design. Registered objects come in three
shapes — a class (`@model class Product`), a callable (`@view def list_products`), and a
value (a registered instance) — so no single `type[T] -> T` signature covers them. The
kernel already "describes, never executes," so a collect-only boot needs no new machinery.
And the identifiers are already canonical and sorted, so a generated artifact is
deterministic by construction.

## Goals / Non-Goals

**Goals:**

- Full editor completion and type checking at existing call sites, with no source change.
- Runtime decoupling between applications preserved exactly as it is today.
- Zero restatement: the developer writes no type they did not already write once.
- Zero runtime dependencies in the base install; nothing new imported by the kernel.
- Drift between the generated artifact and the project is a CI failure, not a silent lie.

**Non-Goals:**

- `KindSpec` gaining a per-kind contract type. Separable; not needed for a typed surface.
- A JSON-Schema manifest or any second emitter (see `docs/ideas/typed-projection.md`).
- Runtime structural validation. The kernel never grows a validation engine.
- Typing `by_kind` / `all` element-wise — they stay `Component[Any]` until kinds carry types.

## Decisions

### 1. Generate a type stub; do not add a typed lookup API as the primary route

A generated stub is the only option where the developer writes nothing new. The alternative
— a typed lookup — costs an import of the module being decoupled from, at every site.

### 2. Emit a stub file (`.pyi`), not a generated module (`.py`)

`docs/ideas/typed-projection.md` proposes a generated `types.py` and then records an open
question: that module imports every domain module, so no domain module may import it. A
stub dissolves the question rather than answering it. A `.pyi` is never imported, never
executed, and cannot create a cycle, so it may reference `apps.catalog.models.Product`
freely while the runtime stays exactly as decoupled as it is today.

### 3. Stub the project's composition root

A `.pyi` shadows the module of the same name for type checking, so the stub must target a
module the project owns. The composition root — `framework.py` in the examples and in the
scaffolder's templates — is that module: it is where `framework` is bound, it is the module
every app already imports, and it is thin by convention (Rule 2), so mirroring its surface
is mechanical. The kind handles it exports are derivable from the declared kind set.

*Constraint this imposes:* the composition root must hold only the framework declaration
and its kind handles. That is already the convention; the design makes it load-bearing, and
the stub generator states it when it encounters anything else.

*Alternative considered:* emitting `typings/spoc/__init__.pyi` to override the installed
package for one project. It types every call site without touching the project's own
modules, but the override is all-or-nothing — the generated stub would have to mirror all of
SPOC's public API, and a partial stub would silently erase the rest. Deferred (Open Q1).

### 4. Literal overloads on `resolve`, with an opt-out fallback

Given `examples/framework.py`:

```python
import spoc

framework = spoc.Framework("models", spoc.KindSpec("views", depends_on=("models",)), "resources")
model = framework.kind("models")
view = framework.kind("views")
```

the generator emits `examples/framework.pyi`:

```python
from collections.abc import Callable
from typing import Any, Literal, overload

from spoc import Component, Framework

from apps.catalog.models import Product      # stub-only: never imported at runtime
from apps.orders.models import Order

class _Root(Framework):
    @overload
    def resolve(self, identifier: Literal["models:catalog.product"]) -> Component[type[Product]]: ...
    @overload
    def resolve(self, identifier: Literal["models:orders.order"]) -> Component[type[Order]]: ...
    @overload
    def resolve(self, identifier: Literal["views:catalog.list_products"]) -> Component[Callable[[], dict[str, Any]]]: ...
    @overload
    def resolve(self, identifier: str) -> Component[Any]: ...      # fallback; omitted under --strict

framework: _Root
model: Callable[..., Any]
view: Callable[..., Any]
```

and the call site is **unchanged**:

```python
product_cls = framework.resolve("models:catalog.product").object
#             ^ completes the identifier string as you type
#                                                          ^ type[Product]
product = product_cls(id=1, name="mouse", price_cents=2900)
product.price_cents        # completes; typo here is a type error
```

The trailing `str` overload keeps dynamically-built identifiers working, at the cost of a
literal typo falling through to `Component[Any]` instead of erroring. `--strict` omits it,
turning every typo into a type error and requiring all resolution to use literals. Default
permissive, opt-in strict.

*Alternative considered:* a generated facade (`types.models.catalog.product`). Better to
read, but it is a second way to say what `resolve` already says — Rule 7 rejects it.

### 5. `Component` becomes generic; `Component[Any]` is the unparameterized meaning

```python
@dataclass(frozen=True)
class Component[T]:          # PEP 695; 3.12+, no dependency, no runtime cost
    identifier: str
    kind: str
    namespace: str
    object_name: str
    object: T
    metadata: Any = field(default=None)
```

Bare `Component` keeps meaning what it means today, so every existing annotation and call
site is unaffected. `Registry.add` returns `Component[Any]`; only the stub narrows it.

### 6. Two typed accessors as the no-codegen escape hatch

Python's type system forces exactly one distinction — `type[T]` versus `T` — so the API has
exactly two methods, not three:

```python
def resolve_type[T](self, identifier: str, contract: type[T]) -> type[T]: ...
def resolve_object[T](self, identifier: str, contract: type[T]) -> T: ...
```

Used with a caller-owned `Protocol`, so `orders` still imports nothing from `catalog`:

```python
from typing import Protocol

class ProductLike(Protocol):                      # declared in orders, about orders' needs
    id: int
    name: str
    price_cents: int
    def __init__(self, *, id: int, name: str, price_cents: int) -> None: ...

product_cls = framework.resolve_type("models:catalog.product", ProductLike)  # type[ProductLike]
```

`resolve_type` checks `isinstance(obj, type)`; `resolve_object` checks the negation. Neither
checks structure — `runtime_checkable` cannot check attribute members anyway, and doing it
would duplicate statically-known facts at runtime. The division is explicit:

```
runtime  →  identity grammar + shape (class | value | callable)
static   →  structure (members, signatures)
```

### 7. Containment and dependency direction

```
        spoc.core  ◀── spoc.stubs        (inward only; core never imports stubs)
                          │
        ┌─────────────────┴──────────────────┐
        │ core (pure)                        │ adapters
        │  describe: Framework → Manifest    │  cli.py      — argv, exit codes
        │  emit:     Manifest → str          │  files       — read/write the .pyi
        └────────────────────────────────────┘  formatter   — byte-stable output
```

`describe` and `emit` are pure functions over in-memory values: no filesystem, no argv, no
process state. Composition wiring lives in `spoc/stubs/cli.py`, mirroring
`spoc/diagnostics/cli.py`. The subpackage follows the containment precedent of `scaffold/`
and `formats/` — nothing in `src/spoc/core/` or `src/spoc/framework.py` imports it. The
describe pass reuses the existing collect-only sequence (`_boot_discovery` without
`loader.initialize`) rather than introducing a second boot path.

### 8. Build-vs-adopt, decided

`/ai:decide` has run; all four decisions are approved and recorded in `DECISIONS.md`.

- **Type-reference extraction** — *Build on stdlib.* The describe pass holds live objects, so
  `__module__`/`__qualname__` and `inspect.signature` answer directly. Every candidate reads
  source statically, which is blind to `[spoc.plugins]` components that exist only after
  configuration resolves.
- **Stub emission and formatting** — *Build the emitter, adopt ruff.* The emitter is driven by
  our own IR; byte-stability comes from `ruff format` and stub linting from ruff's `PYI`
  rules (flake8-pyi, vendored). No new dependency.
- **Stub conformance verification** — *Adopt `assert_type` under three checkers.* See
  Decision 9; this is the one place the gate materially changed shape.
- **IDE autocomplete verification** — *Adopt pyright as the proxy.* Pylance is built on
  pyright, so pyright resolving the type is the evidence completion works.

No base-install dependency is added: extraction is stdlib; formatting, linting, and checking
are dev-group only.

### 9. Conformance is checked by three type checkers, not one

CI currently runs `ty` alone. `ty` is beta at `0.0.x`, ships with an explicit upstream
warning to expect bugs and missing features, and is not what any user's editor runs. Since
this feature's entire promise is *a type checker resolves the promised type*, verifying it
with a checker no user runs would verify the wrong thing — a stub could pass CI and fail
every user's IDE.

Verification is therefore a fixture project of static assertions over a generated stub, run
under all three checkers:

```python
from typing import assert_type
from framework import framework

record = framework.resolve("models:catalog.product")
assert_type(record.object, type[Product])          # mypy + ty

reveal_type(record.object, expected_text="type[Product]")   # pyright: exact rendered type
```

`assert_type` is a runtime no-op, so the fixture also runs as an ordinary test. pyright's
`reveal_type(..., expected_text=...)` asserts the *rendered* type — the string a hover shows
— which is the closest programmatic analogue to what the developer sees in the editor.

*Alternative considered and rejected:* mypy `stubtest`. It is purpose-built for stub/runtime
drift, but it introspects the runtime and would flag `_Root`, which deliberately does not
exist at runtime, and it documents that it cannot verify a return type is accurate — exactly
the claim being made here.

## Risks / Trade-offs

- **The stub can lie if it goes stale.** → `spoc stubs --check` regenerates in memory and
  diffs; wired into `.canon/checks.md` alongside `apicheck`/`apidiff`.
- **Composition roots with extra code lose the surface the stub does not mirror.** → The
  generator refuses rather than emitting a lossy stub, naming the unmirrorable names.
- **Permissive mode silently downgrades a typo to `Any`.** → Accepted default; `--strict`
  is the documented answer, and the docs state the tradeoff rather than hiding it.
- **Degraded entries (`Any`) may read as "typed" when they are not.** → The command reports
  the degraded count; absence over guessing, as the loader already does.
- **A generic `Component` slightly complicates annotations in downstream projections.** →
  Bare `Component` remains valid and means what it means today.
- **Stub generation boots the project.** → Collect-only, no initializers; the same dry-boot
  `spoc check` already performs, with the same containment.
- **Three checkers may disagree on the same stub.** → That disagreement is the signal the
  gate exists to surface. Where they diverge, pyright is authoritative for the autocomplete
  claim (it is what Pylance runs) and the divergence is recorded in the docs rather than
  papered over by loosening the stub.
- **`ty` is beta and may regress on stubs between releases.** → It is one leg of a
  three-checker matrix rather than the sole gate, so a ty regression fails loudly without
  invalidating the feature; mypy and pyright continue to hold the contract.
- **Two type checkers join the dev toolchain.** → Dev-group only, scoped to one fixture
  project and one CI job. The base install and the library's own gate (`ty`) are unchanged.

## Migration Plan

Additive throughout; nothing existing changes meaning.

1. `Component[T]` lands first — bare use is unchanged, so no call site moves.
2. `resolve_type` / `resolve_object` land next; they are new names, reachable or ignorable.
3. `spoc stubs` lands last and writes a file the project may simply not have.

Rollback at any step is deleting the generated stub and the new names; no data, no config,
and no runtime behavior is touched. Projects that never run `spoc stubs` are unaffected.

## Open Questions

1. **Does a later iteration add the `typings/spoc/` override (Decision 3's alternative)?**
   It is the only route to typing call sites in projects whose composition root is not
   mirrorable. Requires a full generated stub of SPOC's public API — plausible, since
   `apicheck` already enumerates it.
2. **Should `spoc check` fail on a stale stub, or stay independent of `spoc stubs --check`?**
   Coherence argues for one dry-boot; separation argues against `check` depending on a file
   most projects will not have.
3. **Do the examples commit their generated stub?** Committing exercises the CI staleness
   gate on a real project; not committing keeps the reference app minimal.
