## 1. Dependency

- [x] 1.1 Add `hypothesis` to the dev group in `pyproject.toml` (with a comment stating why it exists and that it never reaches the published dependency set); sync

## 2. Properties

- [x] 2.1 Grammar properties: conforming-segment generator → compose/parse round-trip identity; adversarial generator (mutations + regex-filtered arbitrary text) → rejection completeness with the grammar's typed errors
- [x] 2.2 Registry state machine: `RuleBasedStateMachine` over register/resolve/enumerate with a shadow model — exactly-once presence, typed duplicate/divergence refusals, deterministic enumeration
- [x] 2.3 Concurrency properties: generated batches with duplicate races through a thread pool — exactly-once, one winner per identifier, deadline disabled

## 3. Validation

- [x] 3.1 Full validation per `.canon/checks.md`; measure and state the suite-runtime impact; budgets adjusted if the whole suite leaves single-digit seconds
- [x] 3.2 Confirm no `src/` change was needed (or, if a counterexample surfaced, stop and report it before fixing)
