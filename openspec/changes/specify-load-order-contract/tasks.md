## 1. Build-vs-adopt gate

- [x] 1.1 Run `/ai:decide` and record the ADR for Decision 1 — whether the order is owned
      as an explicit `(kind_depth, app_index)` key or left to
      `graphlib.TopologicalSorter.static_order()`'s level batching with the behaviour
      documented. `graphlib` stays adopted for cycle detection either way; the decision is
      only about who owns the ordering guarantee.
- [x] 1.2 Confirm the decision against the zero-runtime-dependency invariant — both
      candidates are standard library, so the gate turns on ownership of the contract, not
      on acquisition.

## 2. Pin the current behaviour before changing anything

- [x] 2.1 Add a test asserting the cross-app phase barrier on the *current* implementation:
      two apps, two dependent kinds, assert no app's dependent module loads before any
      app's depended-on module
- [x] 2.2 Add a test asserting the declaration-order tiebreak within one kind phase, in
      both app orders, so the tiebreak is pinned independently of the barrier
- [x] 2.3 Add a test asserting hook firing order matches module load order, and that
      teardown is its exact reverse
- [x] 2.4 Confirm these tests pass unchanged before any production code moves — if any
      fails, the premise of this change is wrong and the proposal needs rewriting rather
      than the code

## 3. Own the ordering rule

- [ ] 3.1 Implement whichever form task 1.1 settled on, keeping `CircularDependencyError`
      raised from the same place with the same message
- [ ] 3.2 Ensure the effective installed-app list is the tiebreak source, so mode cascade
      and duplicate-suppression continue to decide app order exactly as they do today
- [ ] 3.3 Fix the absent-optional-module defect found in task 2: read kind depth from the
      declaration so a module that does not exist cannot pull its app's remaining modules
      into an earlier phase. Flip the strict xfail in `tests/test_load_order.py` to a plain
      test in both app orders
- [ ] 3.4 Confirm `[spoc.plugins]` registrations are unaffected: they populate the registry
      without participating in module load order
- [ ] 3.5 Verify the observable order is byte-identical to the order recorded in task 2 for
      every project where each app declares each kind — the omitted-optional case in 3.3 is
      the one intended difference, and nothing else may move

## 4. Refuse the inversion

- [ ] 4.1 Confirm by inspection that no declaration form can express an edge from a deeper
      kind to a shallower one, and record where that is enforced
- [ ] 4.2 Add a test that whatever ordering exists between apps is confined to one kind
      phase, so a future per-app ordering feature fails here if it breaks the barrier

## 5. Docs and specs

- [ ] 5.1 Add the ordering contract to the invariants list in
      `docs/architecture/kernel.md`, and update any diagram that describes load order so it
      describes what is (Rule 1)
- [ ] 5.2 Document the `[spoc.apps]` order tiebreak where apps are declared, with the
      hook-ordering case as the motivating example
- [ ] 5.3 Ensure any new doc example runs under `tests/test_docs_examples.py`
- [ ] 5.4 Add the CHANGELOG entry: a stated guarantee, plus the one fix — an app omitting
      an optional kind no longer pulls its remaining modules into an earlier load phase.
      Say which is which, so a reader knows exactly what moved and what did not

## 6. Validation

- [ ] 6.1 Confirm `apicheck` reports no new public name (this change adds none) and review
      the `apidiff` surface delta for the same
- [ ] 6.2 Run the full check suite from `.canon/checks.md`; report anything unrunnable as
      unverified rather than assumed passing
- [ ] 6.3 Run `openspec validate specify-load-order-contract --strict`
