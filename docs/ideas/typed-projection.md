# Idea: typed projection — the registry compiled into types

> **Status: partially realized; the remainder is reference.** The `add-typed-registry-access`
> change shipped the typed-access half of this: a collect-only describe pass, a manifest IR,
> and one emitter — but as a **`.pyi` stub** rather than the `types.py` module sketched below.
> That substitution dissolved the import-cycle open question at the end of this document
> instead of answering it: a stub never executes, so nothing constrains which modules may
> import it.
>
> What remains unscheduled is everything downstream of the manifest boundary: the JSON Schema
> serialization, the OpenAPI 3.1 vocabulary call, the per-kind contract seam, and any emitter
> beyond the stub. Those are still kept for the reasoning, not as pending work. See
> `openspec/changes/archive/` for what actually shipped and `docs/docs/how-to/get-editor-autocomplete.md`
> for how it is used.

## Problem

SPOC's one honest DI gap: `resolve("models:catalog.product")` is stringly-typed
service location. A typo is a runtime error; the type checker sees nothing; the IDE
completes nothing. The runtime should stay exactly as it is — dynamic, inert,
grammar-validated — but the _static_ view of the registry is mechanically derivable,
and today we make the developer restate it by hand or go without.

## Inspirations, distilled to what actually transfers

**Strawberry GraphQL** (annotations → schema):

- Python type annotations are the _single source of truth_; the GraphQL schema is
  compiled from the type graph, never written separately.
- **Scalars** are the extensibility seam: a small registry mapping a Python type to
  its leaf-level contract (serialize/parse pair). Adding a scalar never touches the
  compiler — it's data the compiler consults.
- Type resolution is deferred (LazyType/forward refs) until schema-build time, so
  declaration order and import cycles never constrain the author.

**FastAPI / OpenAPI** (runtime objects → standard document → many consumers):

- One introspection pass over live runtime objects (routes, signatures, Pydantic
  models) produces a **standard interchange document** (OpenAPI/JSON Schema).
- The document — not the framework — is the contract surface. Swagger UI, client
  codegen, and validation are all independent _consumers_ of the same document.
  FastAPI never wrote a docs renderer; it wrote a document and adopted renderers.
- Shared types are deduplicated by `$ref` into `components/schemas` — the document
  has its own normalization, separate from Python's.

**The transferable mix** is neither "annotations in" (Strawberry) nor "document out"
(FastAPI) alone — it's the three-stage shape they share:

```
source of truth  →  canonical intermediate model  →  N emitters
(type graph)        (schema / OpenAPI doc)           (SDL, docs UI, clients)
```

## The SPOC version

SPOC already has a _better_ source of truth than either inspiration: the registry is
flat, deterministic, read-sorted, and its names are pre-normalized by the identity
grammar (`kind:namespace.object_name`). No name munging, no dedup heuristics. And the
kernel "describes, never executes," so introspection is a collect-only boot — register
apps, run discovery, skip `initialize()` and all hooks. Side-effect-free by existing
design, not by new machinery.

Three stages, mirroring WHAT/HOW/DO:

### 1. Manifest (the intermediate model — FastAPI's OpenAPI analogue)

A frozen-dataclass IR built from one collect-only pass: every component's canonical
identifier, its Python type reference (module + qualname), its shape
(`class | instance | callable`), its kind's metadata contract, and the kind
dependency edges. **Serializable to JSON Schema** (Rule 9: adopt the standard
interchange) so non-Python consumers exist for free.

The manifest — not the emitter — is the product. `types.py` becomes _one consumer_.

### 2. Kind contracts (the extensibility seam — Strawberry's scalars analogue)

How a component maps to a static type is per-kind data, not compiler logic:

- registered class → `type[X]`
- registered instance → `X`
- kind with a metadata contract → contract type as the upper bound for anything
  the manifest can't see statically (e.g. config-declared plugins resolved late)

A downstream framework declaring a kind can override its mapping (e.g. a `views`
kind might project `Callable[[Request], Response]` rather than the raw class) the
same way `KindSpec` already carries `metadata` and hooks: one frozen record, one
seam, no second structure that can drift.

### 3. Emitters (independent consumers of the manifest)

- **`types.py`** — the frozen-dataclass facade: `SpocTypes.bind(framework)` once at
  the composition root, `types.models.catalog.product` everywhere. Strings survive
  in exactly one generated file. Byte-stable output (deterministic input → sorted
  emit) so it diffs cleanly and CI can check it.
- **`manifest.json`** — the JSON Schema serialization, for anything non-Python.
- Future, cheap because the manifest exists: registry docs page, Mermaid context
  diagram of kind/namespace edges (Rule 1), `.pyi` Literal-overloads for `resolve`
  if the facade ever isn't enough.

## What makes this "more abstract" than plain codegen

The naive version is registry → `types.py` in one script. The mix borrowed from the
inspirations inserts the manifest boundary, which buys:

1. **Emitters never introspect.** They consume a frozen IR. Adding an emitter can't
   break discovery; changing discovery can't silently skew an emitter — the manifest
   schema is the contract between them.
2. **Extension without modification.** New kinds bring their own type mapping
   (scalars lesson); new outputs are new emitters (OpenAPI lesson). The compiler
   core never grows per-kind or per-output branches.
3. **Staleness is checkable at the right layer.** `spoc types --check` regenerates
   the manifest in memory and diffs — same discipline as `/opsx:sync`, and it
   catches drift in _any_ emitted artifact, not just `types.py`.

## Schema vocabulary: adopt OpenAPI 3.1 = JSON Schema 2020-12

Rule 9 already mandates the standard; the sharp edge is the version. Adopt **JSON
Schema 2020-12 + the OpenAPI format registry** (what OAS 3.1 uses verbatim), _not_
the OAS 3.0 subset dialect (`nullable:` etc.) whose divergence the ecosystem spent
years unwinding. Then manifest schemas can be `$ref`'d into any OAS 3.1 document
with zero translation.

- **Interiors become staged, not deferred.** A component whose fields/metadata are
  describable carries a `schema` field: standard types + formats (`date-time`,
  `uuid`, `int64`, …) + constraints (`minLength`, `pattern`, `minimum`, …). A
  downstream framework with a `views` kind derives `openapi.json` nearly free —
  paths from `by_kind("views")`, `components/schemas` from the manifest. FastAPI's
  trick, generalized to any kernel-built framework.
- **Python authoring side:** adopt the `Annotated` + `annotated-types` vocabulary
  (`MinLen`, `Ge`, `Pattern` — the Pydantic v2/msgspec/FastAPI convention), which
  maps ~1:1 onto JSON Schema keywords. Adopt the vocabulary; whether to hand-roll
  the small `annotated-types → keywords` mapping over stdlib dataclasses or rent a
  deriver is an `/ai:decide` call. Derivation machinery lives behind a `spoc[schema]`
  extra either way — the base install stays zero-dependency.
- **Describe, never execute — held at the schema layer too.** In 2020-12, `format`
  is an annotation, not an assertion, by default. SPOC emits schemas; validation is
  rented from any conformant validator in any language. **SPOC never grows a
  validation engine** — the moment the kernel checks `minLength` at runtime it has
  become Pydantic with extra steps.
- **The mapping is partial, honestly.** `Callable`, `Protocol`, unannotated classes
  have no faithful schema → those components carry no `schema` field. Absence over
  guessing (same rule as the loader's absent ≠ broken).

## Open questions (for the proposal, not for here)

- Collect-only boot: expose as a real kernel mode (`framework.describe()`?) or keep
  it a compiler-internal use of existing pieces? Kernel purity says the latter until
  proven otherwise.
- Import-cycle rule: `types.py` imports every domain module, so no domain module may
  import it at module level (`TYPE_CHECKING` or parameter injection only). State it
  in the spec; don't discover it in a bug report.
- Where does the emitter live — `spoc/` subpackage the kernel never imports (like
  `scaffold/`, `formats/`), surfaced as `spoc types`? Almost certainly yes.
- `/ai:decide` pass: JSON Schema emit via stdlib-only hand-rolling vs. adopting a
  schema library — and whether any existing Python codegen tool (e.g. the
  datamodel-code-generator family works the _other_ direction) is worth adopting.
  Suspected answer: Build for the facade emitter (~one stdlib file driven by our own
  IR), Adopt the JSON Schema vocabulary but not necessarily a library.
- Zero-runtime-dependency mandate: everything above must hold under the base
  install. Nothing here needs a dependency; keep it that way.
