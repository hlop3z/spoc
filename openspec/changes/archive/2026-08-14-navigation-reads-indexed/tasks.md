# Tasks: reading one facet costs the facet

## 1. Pin the property (red first)

- [x] 1.1 Add the scale test: navigation walk cost with N components in the target
  facet must stay within a constant factor when k·N components are registered in
  *other* facets (design D3 — ratio, not wall-clock; bound an order of magnitude
  looser than the effect). Include the same ratio check for `by_kind` and
  `namespaces(kind)`.
- [x] 1.2 Run it against the current scan-based reads and confirm it fails — the
  measured 30,000× gap is the red.

## 2. The index

- [x] 2.1 Add `_facets` (kind → namespace → object name → record) to `Registry`,
  written inside the existing locked block in `add()`, beside the `_store` write —
  one lock, one atomic admission (design D1).
- [x] 2.2 Move `by_kind`, `by_namespace`, and `namespaces` onto the index: snapshot
  the facet under the lock, sort outside it (design D2). `all()`/`__iter__` stay on
  the store.
- [x] 2.3 Add the internal object-names read for one (kind, namespace) facet; move
  navigation's `_namespaces()`/`_object_names()` onto the faceted reads.
- [x] 2.4 Confirm failure paths are untouched: `resolve`'s one-observation failure
  walk and navigation's candidate lists still come from a single snapshot, with the
  same candidates as before. Verified: all three failure messages unchanged.

## 3. Validation (Rule 6 — `.canon/checks.md`)

- [x] 3.1 `uv run pytest` — full suite; the registry property tests (generated
  operation sequences, concurrency invariants) and the navigation suite must pass
  unchanged, since behavior is identical.
- [x] 3.2 Re-run the 50k benchmark from the proposal by hand; record before/after in
  the commit message: 10.62 ms -> 1.72 us per walk (6,175x), registration unchanged.
- [x] 3.3 `uv run ruff format --check .`, `uv run ruff check`, `uv run ty check`,
  `uv run mypy`.
- [x] 3.4 `task check` — full gate.

## 4. Close out

- [x] 4.1 `/opsx:sync` — fold the `component-registry` delta into the main spec.
- [x] 4.2 `openspec archive -y --skip-specs`, commit and merge per Rules 3–5.

## 5. Found during apply (see design D2a and the spec delta)

- [x] 5.1 Indexing alone left every *successful* step sorting its facet for an order
  the success path never reads. Added `Registry.holds(...)` — the membership question
  at whatever depth a caller has reached — and navigation asks it first, falling back
  to the ordered facet only for an escaped spelling or a failure's candidate list.
- [x] 5.2 The `Single flat store` requirement said grouped views must "never be
  maintained as independent state", which read literally forbids this index. Amended
  to forbid the hazard (a view that could disagree) rather than the mechanism, with a
  new scenario pinning that no view is observable without the others.
- [x] 5.3 Added the concurrency test for that scenario: readers hammer the facets and
  the store while a writer registers, asserting the views never disagree.
- [x] 5.4 Corrected the registry module docstring, which claimed facets are "derived on
  read, never maintained" — untrue as of this change (Rule 8).

## 6. Review outcome: keep the structural guarantee (see design D1 revised, D1a)

- [x] 6.1 Replaced the store-plus-index implementation with a single store keyed by the
  grammar's segments; deleted the flat identifier-keyed dict rather than adding to it.
  A facet is now a sub-dictionary of the one store, so drift is unrepresentable again.
- [x] 6.2 Reverted the weakening of `Single flat store`. It keeps its original wording —
  grouped views derived, never maintained — plus one addition covering the non-derivable
  identity map: such state is written in the same atomic step and must be enumerable.
- [x] 6.3 Added `_admit` as the registry's only mutator, and the AST test that fails if a
  second writer appears. Mutation-checked: a bulk-add that forgets the identity map is
  caught, named, and its touched attributes listed.
- [x] 6.4 `__contains__` keeps answering `False` for a malformed identifier rather than
  raising, now that the lookup parses; pinned by test.
- [x] 6.5 Re-measured: navigation 10.62 ms → 1.92 µs (5,531x). `resolve` failure
  6,500 → 63.5 µs (102x), unplanned — the failure path stopped copying the store.
  `resolve` success 0.31 → 0.42 µs, the accepted cost of three hits instead of one.
