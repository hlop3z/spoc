## Context

The contracts under test already exist and pass example-based tests
(`test_identity.py`, `test_registry.py`, `test_concurrency.py`). This change
adds universal quantification over the same public API — `spoc.parse`,
`spoc.compose`, `Identifier`, `Registry` — with no `src/` changes expected.
The property-testing library is a critical-concern adoption (a test *engine*,
with shrinking and stateful exploration, is never hand-rolled) and goes
through /ai:decide.

## Goals / Non-Goals

**Goals:**
- One property file per contract family, runnable in the normal `pytest`
  gate with a bounded, stated example budget.
- Grammar: round-trip identity and rejection completeness driven by two
  generators — conforming segments, and adversarial non-conforming strings.
- Registry: Hypothesis `RuleBasedStateMachine` over register/resolve/
  enumerate with a shadow model dict; refusals asserted to be the exact typed
  errors.
- Concurrency: generated batches (sizes, duplicate ratios) run through a
  thread pool; postcondition checks exactly-once presence and one winner per
  identifier.

**Non-Goals:**
- No fuzzing of the loader/filesystem surface (slow, and the harness tests
  cover it); no Hypothesis profiles wired into CI knobs beyond the stated
  budget; no replacement of existing example tests.

## Decisions

### D1 — Layout: `tests/test_properties.py`, sectioned like the suite
One file, three sections (grammar / registry state machine / concurrency),
mirroring the suite's per-concern docstring style. Property tests import
only public API (`spoc.parse`, `spoc.compose`, `spoc.Registry` via
`spoc.core.registry` as the existing tests do).

### D2 — Example budget: explicit `settings(max_examples=...)`
A stated budget per test (grammar tests high, state machine moderate,
concurrency low) keeps `task check` fast and makes the cost a reviewed
number. Deadline disabled for the concurrency batch (thread scheduling
jitter would flake it).

### D3 — Adversarial generator strategy
Non-conforming inputs are generated, not enumerated: mutations of valid
identifiers (case flips, unicode letters, empty segments, wrong separators,
whitespace, surrogates) plus arbitrary text filtered against the grammar
regex — so acceptance is checked against the regex as the single source of
truth, and any disagreement between implementation and stated grammar
surfaces as a counterexample.

### Decision: Property-testing engine — Adopt Hypothesis

- **Status**: approved
- **Why**: The category is never hand-rolled (shrinking, replay databases,
  and stateful exploration are subtle machinery); Hypothesis is the Python
  standard — actively maintained, stateful testing built in, pytest-native,
  MPL-2.0. Dev group only; the published `dependencies = []` is untouched.
- **Considered**: atheris (coverage-guided fuzzing — C-oriented harness,
  wrong shape for API properties); schemathesis (API-schema fuzzing — wrong
  layer; itself built on Hypothesis).
- **Isolation**: `tests/` only. No `src/` import may name it; the published
  distribution never sees it.

## Risks / Trade-offs

- [Flaky properties under CI jitter] → deadline disabled where threads are
  involved; budgets stated; failures replay deterministically via
  Hypothesis's example database (kept out of git via existing ignores).
- [A property finds a real kernel bug mid-change] → that is the point; the
  fix is its own change, and the shrunken counterexample lands as a named
  regression test.
- [Longer suite runtime] → budgets chosen to keep the whole suite in single-
  digit seconds; measured in the validation task.

## Migration Plan

Purely additive to `tests/` and the dev group. Rollback: remove the file and
the dependency line.

## Open Questions

None.
