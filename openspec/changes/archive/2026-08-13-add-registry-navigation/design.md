## Context

Three measurement ladders were run this session (2026-08-13) against synthetic stubs
in the shipped emitter format, mypy 2.3.0 / pyright 1.1.411 / ty 0.0.66, on the
development machine. They are the evidence this design stands on.

**Checking wall-time, Literal-overload shape (current design):**

| n | stub | mypy | pyright | ty |
|---|---|---|---|---|
| 100 | 13 KB | 1.2 s | 0.8 s | 0.1 s |
| 500 | 63 KB | 2.7 s | 0.9 s | 0.1 s |
| 2,000 | 254 KB | 27.5 s | 2.0 s | 0.1 s |
| 10,000 | 1.3 MB | timeout >300 s | 33.0 s | 0.5 s |
| 50,000 | 6.4 MB | — | crash (V8 heap, exit 134) | 8.6 s |

A strict-mode typo at n=2,000 produces a 232 KB / 2,002-line mypy error (every
overload enumerated). pyright stays at 6 lines but names the *last* overload as the
expected type. ty caps its diagnostic at a constant 67 lines.

**Checking wall-time, accessor-tree shape (this change):**

| n | stub | mypy | pyright | ty | typo error |
|---|---|---|---|---|---|
| 100 | 6 KB | 1.3 s | 0.8 s | 0.0 s | 1 line / 5 / 7 |
| 2,000 | 76 KB | 1.2 s | 0.7 s | 0.1 s | constant |
| 10,000 | 372 KB | 1.4 s | 0.8 s | 0.1 s | constant |
| 50,000 | 1.9 MB | 2.4 s | 1.2 s | 0.2 s | constant |

mypy's tree typo error names near-miss candidates ("maybe `model_200`,
`model_1000`, or `model_1200`?") — one line, 138 chars.

**Editor completion (language servers over stdio, cold = first request after open,
warm = steady state):**

| shape | n | pyright cold/warm | items | ty cold/warm | items |
|---|---|---|---|---|---|
| overload | 2,000 | 1.27 / 0.83 s | 2,001 | 0.19 / 0.00 s | 1,000 |
| overload | 10,000 | 21.4 / **18.8 s** | 10,001 | 2.4 / 0.0 s | **0 (gives up)** |
| tree | 10,000 | 0.35 / 0.02 s | 224 | 0.07 / 0.00 s | 223 |
| tree | 50,000 | 0.69 / **0.02 s** | 1,024 | 0.27 / 0.01 s | 1,000 |

The tree's item counts are structural: ~50 namespaces at one level, then only that
namespace's members — the grammar is the filter. The overload list is the whole
project inside one pair of quotes.

Constraints carried in from existing specs: the stub derives from the projection
(typed-registry-stubs), typed access is a pure lookup that never verifies structure
(typed-component-access), stubs are inert at runtime, generation is deterministic,
and emitted descriptions must be diagnostic-free under the declared checker set in
every emission mode (added by `fix-strict-stub-suppression`).

## Goals / Non-Goals

**Goals:**

- A navigation surface whose static description stays verifiable and instant at
  50,000 components in every conformance checker.
- Per-segment editor completion and one-line member-level typo errors.
- Zero restatement: the surface is derived from the registry; nothing is declared
  twice (the automate-what-the-kernel-can-derive principle).
- The existing overload stub keeps working unchanged below the guard threshold.

**Non-Goals:**

- Replacing `resolve()` or changing its semantics; dynamic identifiers stay there.
- The warn-mode (`@deprecated` tail) emission variant — separate future change.
- Cross-language navigation surfaces; the registry *projection* remains the
  language-neutral artifact.

## Decisions

### D1 — A dedicated navigation attribute whose members are only grammar names

The runtime surface is one object reachable from the framework, whose attributes are
exactly the declared kinds; each kind's attributes are exactly its namespaces; each
namespace's attributes are exactly its object names, yielding the same record
`resolve` yields. It is a *dedicated* object rather than attributes grafted onto
`Framework` or the registry, because those classes have methods, and a method name
is exactly the collision a kind name must never lose to. On the dedicated object the
member set is grammar-only, so the only collision class left is language reserved
words (D4).

**Alternatives considered:**
- *Attributes on the existing registry object.* Rejected: `resolve` and friends
  already live there; a kind named like any current or future method would shadow or
  be shadowed.
- *A generated module instead of a runtime object.* Rejected: a module would be
  imported by user code, coupling apps to a generated artifact at runtime;
  typed-registry-stubs' inertness requirement exists precisely to prevent that.

### D2 — Runtime derivation is lazy attribute lookup, not codegen

The runtime object answers attribute access by consulting the registry at access
time (with the registry's own read-consistency rules); nothing is materialized up
front and no runtime code is generated. This is what "derived" means concretely: the
tree cannot disagree with the registry because it *is* the registry, read through
another spelling. Failure at any segment carries the same precision as identifier
resolution — the segment that failed, and the candidates at that segment — reusing
the registry's existing per-segment error machinery rather than duplicating it.

### D3 — The static description renders the tree as nested typed members

The emitter describes the navigation object as nested classes with typed attributes
— the exact shape measured flat at 50,000 components in all three checkers, both for
checking and completion. It joins the same generated stub file, derives from the
same manifest (which derives from the projection), and is covered by the same
determinism, staleness (`--check`), and diagnostic-free conformance requirements as
the rest of the stub. Strict and permissive modes emit the identical tree: the tree
is inherently "strict" (an undeclared member is an error by nature) without any
suppression, because nothing about it overrides a base-class method.

**Alternatives considered (all measured, all rejected on the data above):**
- *Flat Literal overloads at scale* — the ladder this change exists to escape.
- *Named `Identifier` alias tail* — improves one checker's error text, removes no
  suppression, does not change the scaling class.
- *`Component[Never]` tail* — silent in two checkers (bottom type flows everywhere);
  strictly worse than permissive.
- *`@deprecated` / `LiteralString` tails* — genuinely promising for warn-mode UX but
  orthogonal to scale, unsupported by one checker, collapsed by another; deferred as
  its own change.

### D4 — Reserved-word segments escape with a trailing underscore

A grammar segment that is a language reserved word is exposed with a trailing
underscore (`class` → `class_`), the same deterministic escape the scaffold already
applies to generated kind variables, applied at both the runtime surface and the
static description so the two can never disagree. The identifier string is
untouched — escaping is a property of the member spelling, not the identity.

### D5 — The size guard reports; it does not refuse

When identifier-narrowed (overload) emission exceeds a documented threshold, the
generator emits the stub anyway and reports: the count, the threshold, why it exists
(named checker behavior at scale), and that the navigation surface is the supported
shape past it. The default threshold is **1,000 entries** — below mypy's measured
superlinear knee (~2,000) and below the completion degradation onset — recorded as a
documented constant with the evidence beside it. Refusing was rejected: a ty-only
consumer is fine at 50,000, and a guard that blocks them enforces a limit they do
not have. The threshold is a constant, not configuration: its only wrong values are
ones the evidence contradicts.

### Build-vs-adopt

No external tool decision arises: the runtime surface is stdlib-only derivation over
the existing registry, and emission extends the existing emitter. The checkers
consulted are the already-adopted conformance set. Nothing to record via `/ai:decide`.

## Risks / Trade-offs

- **[Two typed surfaces to teach]** `resolve("kind:ns.name")` and navigation both
  exist → the docs frame them as one grammar with two spellings — the string for
  dynamic access, the members for static access — and the guard message points from
  one to the other at the scale boundary.
- **[Stub size at extreme scale]** 1.9 MB committed stub at 50,000 components →
  linear, 3.4× smaller than the overload shape at the same n, and `--check` keeps it
  honest; no action beyond documenting it.
- **[Completion list at one level can still be ~1,000 items]** at n=50,000 →
  measured at 0.02 s to produce; editors filter as the user types. Accepted.
- **[A checker changes its member-completion behavior]** → the conformance gate now
  reads the tree's assertions in all three checkers, so a regression is detected the
  way `fix-strict-stub-suppression` made suppressions detectable.
- **[Kind/namespace named like a dunder or `object` member]** (`keys`, `items` are
  fine on a bare object, but `__class__`-like names are not) → the grammar already
  restricts segments to lowercase snake_case identifiers; dunder names are not valid
  grammar and the emitter refuses what the grammar refuses. Verified in tests.

## Migration Plan

Additive, minor-release surface under the post-1.0 policy: new export, new stub
content, no existing element changes. Projects regenerate stubs with `spoc stubs`
on upgrade; committed stubs fail `--check` until regenerated, which is the staleness
mechanism doing its job. Rollback is deleting the stub content and not using the
attribute — nothing else moves.

## Open Questions

- ~~The navigation attribute's name~~ **Settled at apply time: `objects`.**
  `framework.objects.models.shop.product` — the grammar's own word for the thing
  being reached (`kind:namespace.object_name`), and the shortest candidate. Declined:
  `components` (stutters against the `Component` record type, and longer for no gain),
  `registry` (unavailable — `Framework.registry` is the store), `tree` (names our
  implementation shape rather than the user's subject).
- ~~Whether the LSP completion rig graduates from scratchpad spike to a workshop
  tool~~ **Settled at apply time: promoted to `scripts/py/lab/completion_bench.py`**,
  a single PEP 723 file, per the workshop's own rule for a tool whose shape is still
  unknown and whose use is occasional. Not `py/tools/`: it is not yet recurring and
  has no suite of its own, and promotion is one-directional and cheap if it earns it.
  It takes a workspace and a cursor position rather than generating stub shapes
  itself, so it can measure a shape nobody has proposed yet. Reproduced the 50k tree
  numbers on first run (pyright 0.02 s warm / 1,024 items; ty 0.00 s / 1,000).
