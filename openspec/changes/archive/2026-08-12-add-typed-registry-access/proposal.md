## Why

Resolving a component returns `Component.object` typed `Any`, so every consumption site
loses the type it just looked up: no completion, no member checking, and a mistyped
identifier fails at runtime instead of in the editor. The obvious fixes all cost more than
they return — annotating the result restates a type the registry already knows, and passing
the expected type to the lookup forces a runtime import of the very module the registry
exists to decouple from (`examples/apps/orders/views.py` resolves `models:catalog.product`
precisely so `orders` never imports `catalog`).

The registry already holds everything a type checker needs, and the kernel already
describes without executing. The static view is mechanically derivable; today we make the
developer restate it by hand or go without.

## What Changes

- **Registry records carry their object's type.** `Component` gains a type parameter so
  `component.object` can be described as something other than `Any`. Unparameterized use
  keeps today's behavior, so no existing call site changes meaning.
- **A describe-only pass over a project.** Registering apps and running discovery without
  running module initializers or lifecycle hooks, yielding each record's identifier, its
  shape (`class`, `instance`, or `callable`), and a reference to its Python type.
- **A generated type-stub artifact.** A new CLI verb emits a stub describing the resolution
  surface of a booted project: per-identifier overloads that give the exact static type of
  `.object`, and identifier strings the editor can complete and the checker can reject when
  misspelled. The stub is inert at runtime — it never executes, never imports, and therefore
  cannot re-couple the apps it describes.
- **A staleness gate.** The same command can verify a committed stub still matches the
  project instead of rewriting it, so drift is a CI failure rather than a silent lie.
- **Structural access without generation.** A resolution accessor that takes a caller-owned
  `Protocol` and returns the record's object typed as that protocol, for projects that do
  not want a generated artifact. The consumer declares the shape it needs in its own module
  and still never imports the provider.
- **Docs.** A typed-access guide covering both routes and their tradeoffs.

Not in scope: `KindSpec` gaining a per-kind contract type, a JSON-Schema manifest, any
emitter other than the stub, and any runtime structural validation. Each is separable and
none is needed to make the surface typed.

## Capabilities

### New Capabilities

- `typed-registry-stubs`: describing a booted project's resolution surface as a generated,
  runtime-inert type stub — what it must contain, how identifiers and shapes map to static
  types, what happens when a type cannot be described faithfully, determinism of the output,
  and verifying a committed stub against the project.
- `typed-component-access`: obtaining a registry record's object under a caller-supplied
  type without importing the providing module — what is checked at resolution time, what is
  deliberately left to the type checker, and how the three component shapes are told apart.

### Modified Capabilities

- `component-registry`: a registry record's described object type becomes part of the
  record's contract rather than being unconstrained; enumeration and identity behavior are
  unchanged.

### Critical concerns for `/ai:decide`

Named here, tool deliberately deferred:

- **Type-reference extraction** — recovering a faithful static type reference for a
  registered class, instance, or callable. Correctness-sensitive: a wrong reference produces
  a stub that lies to the type checker. This project already has an adopted API-extraction
  tool, so extend-versus-build is a live question.
- **Stub emission and formatting** — producing byte-stable, checker-valid stub text.
- **Stub validity verification** — confirming emitted stubs are well-formed and that the
  types they promise are the types resolution actually yields.

## Impact

- `src/spoc/core/registry.py` — `Component` gains a type parameter.
- A new subpackage for the describe pass and stub emitter, imported by no kernel module,
  following the containment precedent of `scaffold/` and `formats/`.
- The CLI gains one verb; `spoc.testing` gains nothing.
- `docs/` gains a typed-access guide; its examples run under the existing docs-example gate.
- The public API surface grows, so the existing stability-tier and surface-diff gates apply
  to the new names.
- Zero runtime dependencies must still hold for the base install; anything adopted for
  extraction or emission belongs behind an extra or a dev group.
- No behavior change at runtime: resolution, discovery, and lifecycle are untouched.
