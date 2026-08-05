## Why

The suite's 461 tests are example-based: they prove the cases their author
thought of. The kernel's two hardest contracts — the identifier grammar and
the registry's concurrency guarantees — are exactly the kind whose failures
live in the cases nobody thought of. Property-based testing states each
contract once and lets generated inputs and interleavings hunt for the
counterexample; for a one-author project it is the closest available proxy
for strangers running the code.

## What Changes

- Property tests for the identifier grammar: compose→parse round-trip
  identity over all conforming segments, and rejection completeness — any
  string violating `^[a-z][a-z0-9_]*$` (or the identifier shape) is refused,
  never partially accepted or silently converted.
- Stateful property tests for the registry: under arbitrary generated
  sequences of register/resolve/enumerate operations, the invariants hold —
  atomic acceptance, exactly-once presence, duplicate/divergence refusals,
  deterministic enumeration.
- Property tests for the concurrency contract: generated batches of
  concurrent registrations (including deliberate duplicate races) always end
  in a consistent registry with one winner per identifier.
- The property-testing library joins the **dev group only** — the published
  `dependencies = []` invariant is untouched.
- Example-based tests stay: properties add universal quantification, they do
  not replace the readable named cases.

## Capabilities

### New Capabilities

<!-- none — no new behavior; existing contracts are strengthened -->

### Modified Capabilities

- `object-identity`: the "Single identifier grammar" requirement gains
  universal scenarios — round-trip identity and rejection completeness over
  the whole input space, not just named examples.
- `component-registry`: the "Registration is safe under concurrency"
  requirement gains a universal scenario — the invariants hold under any
  generated operation sequence and interleaving.

## Impact

- New code: `tests/test_properties.py` (or split per concern); dev-group
  dependency addition in `pyproject.toml`.
- No `src/` changes expected; if a property finds a real counterexample, the
  fix is its own change with its own regression test.
- CI: the property suite runs in the normal `pytest` gate with a bounded
  example budget so `task check` stays fast; the budget is a stated number,
  not a default nobody chose.
