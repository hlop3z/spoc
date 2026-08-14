# Tasks: distinct revisions stay distinct on the host that stores them

## 1. Make the guard test the right equivalence (red first)

- [x] 1.1 In `tests/test_properties.py`, replace the `_entry(left) != _entry(right)`
  assertion with injectivity under an explicit model of the coarsest host equivalence:
  compare `entry.name` lower-cased with trailing dots and spaces stripped (design D2),
  named once as `_as_the_store_sees_it`. The pair strategy also had to change to reach
  the colliding region at all — recorded as design D2a.
- [x] 1.2 Run the property test and confirm it fails on both instances — the case pair
  hypothesis already found, and a trailing-dot pair (`v1.` / `v1`) the old assertion let
  through. Red on `('A', 'a')` every run; the trailing-dot clause was then mutation-
  checked separately and killed by `('1', '1.')`, so both clauses are load-bearing.
- [x] 1.3 Add the two instances as named examples in `tests/test_scaffold_cache.py`
  under `TestRevisionNamesItsOwnContent`, so the defect stays pinned by a case a reader
  can see without running hypothesis.

## 2. Narrow the verbatim branch

- [x] 2.1 In `DirectoryCache._entry` (`src/spoc/scaffold/cache.py`), admit the verbatim
  branch only for a revision that matches `_SAFE_SEGMENT`, is not `.` or `..`, contains
  no uppercase letter, and does not end in `.` (design D1). Everything else falls
  through to the existing digest branch — no new branch, no new mechanism.
- [x] 2.2 Update the `_entry` docstring: state that *faithful* means the host stores the
  name it was given, and that this is why case and trailing dots take the digest. Remove
  the claim that nothing retained before the mapping is invalidated — this change does
  invalidate mixed-case and trailing-dot entries, and the docstring must not say
  otherwise (Rule 8).
- [x] 2.3 Confirm the pinned verbatim cases still hold: `a1b2c3d4`, `v1.0.0`,
  `release-1_0`, and the resolver's `url-<digest>` key all stay verbatim.

## 3. Validation (Rule 6 — `.canon/checks.md`)

- [x] 3.1 `uv run pytest` — full suite green, including the property tests that opened
  this change.
- [x] 3.2 `uv run pytest tests/test_properties.py -p no:randomly` a second time with the
  `.hypothesis` example database cleared, so the pass is a real search rather than a
  replay of stored examples.
- [x] 3.3 `uv run ruff format --check .`, `uv run ruff check`, `uv run ty check`.
- [x] 3.4 `cd scripts/py && uv run apicheck ../..` — `_entry` is internal, so the public
  surface must be unchanged; confirm rather than assume.

## 4. Close out

- [x] 4.1 `/opsx:sync` — fold the `remote-template-acquisition` delta into the main spec.
- [x] 4.2 `openspec archive -y --skip-specs`, then commit and merge per Rules 3–5.
