## Why

Typed access does not survive the projects SPOC exists for. The current static
description narrows `resolve` per identifier, and every number measured this session
says that shape collapses at Django scale: of the three checkers in the declared
conformance set, one becomes superlinear at ~2,000 components and dies at 10,000,
another crashes its own runtime at 50,000, a single misspelled identifier produces a
232 KB error at 2,000, editor completion takes 18.8 seconds per request at 10,000 in
the engine behind Pylance, and the third checker silently stops offering completions
entirely. The same registry rendered as *member navigation* — the shape every checker
has optimized for decades — is flat across the whole ladder: ~1–2 s to check and
0.02 s to complete at 50,000 components, with one-line "did you mean" typo errors.
The registry's own grammar, `kind:namespace.object_name`, maps 1:1 onto that shape.

## What Changes

- A **typed navigation surface over the registry**: a derived runtime object that
  exposes registered components along the identity grammar's segments —
  kind, then namespace, then object name — each step a pure lookup yielding the same
  record identifier resolution yields. No component is declared twice: the surface is
  derived from the registry, and a name that collides with a language reserved word
  stays reachable through a deterministic, documented escape.
- **Static description of that surface** joins the generated stub: the navigation
  object is described as nested typed members, giving editors per-segment completion,
  concrete component types, and typo errors at the exact member that is wrong —
  verified diagnostic-free by the conformance gate like the rest of the stub, and
  verifiably so at Django-and-beyond registry sizes.
- **A size guard on identifier-narrowed emission** (existing stub shape): generating
  the per-identifier narrowing past the scale where the declared checker set is
  measured to degrade now reports the situation and points at the navigation surface,
  instead of silently emitting a stub that times out a consumer's CI or freezes their
  editor. Emission still happens — the guard informs, it does not refuse.
- Dynamic identifiers remain `resolve()`'s job, unchanged: navigation is inherently a
  literal path, and the split matches typed-component-access's philosophy — static
  concerns to the checker, runtime access stays a pure lookup.

Not in scope: changes to `resolve()` semantics or its overload emission below the
guard threshold; the warn-mode/deprecated-tail ideas from the same exploration
(separately shaped, deliberately deferred); removal of anything.

## Capabilities

### New Capabilities

- `typed-registry-navigation`: navigating the registry along identity-grammar
  segments as a typed, derived, pure-lookup surface — its runtime behavior, its
  static description, and the scale at which both must remain verifiable.

### Modified Capabilities

- `typed-registry-stubs`: add a requirement that emission of the identifier-narrowed
  description past the scale the declared checker set is known to support MUST be
  reported to the operator, naming the threshold and the alternative surface.

## Impact

- `src/spoc/` — a runtime navigation object derived from the registry (kernel-side
  surface, no new dependency), plus its export and stability tier.
- `src/spoc/stubs/` — manifest and emitter extended to describe the navigation
  surface; size guard in generation.
- `tests/` — conformance fixture regenerated; navigation assertions beside the
  existing ones in all three checkers; unit tests for derivation, purity, failure
  parity, keyword escape, determinism, and the guard.
- `docs/` — stubs and typed-access pages gain the navigation surface; stability page
  tier for the new export.
- `apidiff` will report added public surface — a minor-release addition under the
  post-1.0 policy, no breakage.
- Evidence base: three measurement ladders (checking, error volume, completion) from
  this session's exploration, recorded in `design.md`.
