# Rename `meta` to `metadata`: one vocabulary for one concept

## Why

The declaration surface spells one concept two ways: registration accepts the keyword
`meta`, but the value it carries lands in fields named `metadata` (`Component.metadata`,
`KindSpec.metadata`, `Internal.metadata`), and the main specs speak only of "metadata".
The project's own naming invariant — one grammar, used identically everywhere — is
violated by its own registration kwarg. The 1.0 tag is not yet cut, so this rename is
free today; the day the tag exists it costs a major release and a full deprecation
lifecycle.

## What Changes

- **BREAKING**: the keyword parameter for supplying component metadata is renamed
  `meta` → `metadata` on the public `component()` marker and on every kind
  registration handle (`KindHandle`). Permitted without deprecation under the
  pre-1.0 allowance (`release-policy`); the surface-delta gate reports it.
- Internal alignment: `check_metadata` and the registrar's inner closure use the same
  spelling, so the word `meta` no longer appears in the declaration layer.
- Tests and docs that pass `meta=` are updated (5 test call sites, 2 docs pages).
- If the generated-stub emitter or the committed conformance fixture spells the
  kwarg, they are regenerated; the `spoc stubs --check` gate verifies.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `framework-declaration`: the metadata-contract requirement gains the vocabulary
  constraint — every surface that accepts component metadata MUST name it
  `metadata`, matching the registry record and the kind declaration, so the
  registration keyword can never diverge from the field it populates again.

## Impact

- `src/spoc/core/declaration.py` — `component()`, both `KindHandle` overloads, the
  registrar closure, `check_metadata` (~8 lines).
- `tests/test_declaration.py` (3 sites), `tests/test_framework.py` (2 sites).
- `docs/docs/learn/framework.md`, `docs/docs/api/errors.md`; `docs/site/` is
  regenerated output.
- `tests/conformance/` fixture only if it spells the kwarg (verify, regenerate).
- Surface delta (`apidiff`) records an incompatible change, permitted pre-1.0.
- No dependency changes; no schema changes; the projection document is untouched
  (its field was already `metadata`).
