# Tasks: rename `meta` to `metadata`

## 1. Source rename

- [x] 1.1 In `src/spoc/core/declaration.py`, rename the keyword `meta` → `metadata` on
  `component()`, both `KindHandle.__call__` overloads, and the registrar's inner
  `register`/`decorator` closures; rename `check_metadata`'s `meta` parameter and
  locals to match.
- [x] 1.2 Sweep `grep -n "\bmeta\b" src/spoc/core/` — must return nothing. Sweep the
  rest of `src/spoc/` for `meta=` call sites (none expected; `scaffold/sources.py`'s
  local `meta` variable is template-set metadata, unrelated — leave it or rename for
  hygiene, reviewer's call).

## 2. Tests

- [x] 2.1 Update `tests/test_declaration.py` (3 sites) and `tests/test_framework.py`
  (2 sites) to pass `metadata=`.
- [x] 2.2 Add one declaration test asserting the registration handle accepts
  `metadata=` and that `meta=` raises `TypeError` — pins the spec's one-name scenario.

## 3. Docs

- [x] 3.1 Update `docs/docs/learn/framework.md:98` (`@view(meta=…)` → `metadata=`).
- [x] 3.2 Update the `MetadataContractError` row in `docs/docs/api/errors.md:53` —
  grep-verified, since table cells are outside the snippet suite.
- [x] 3.3 Grep `docs/docs/` for any remaining `meta=`; `docs/site/` regenerates.

## 4. Generated artifacts

- [x] 4.1 Check whether `src/spoc/stubs/emit.py` or the committed
  `tests/conformance/` fixture spells `meta=`; regenerate the fixture if so.

## 5. Validation (Rule 6 — `.canon/checks.md`)

- [x] 5.1 Run `task check` (formatter, linter, ty, full pytest incl. conformance and
  docs snippets, docs build, apicheck, apidiff).
- [x] 5.2 Confirm `apidiff` reports the rename as a pre-1.0-permitted incompatible
  change and nothing else unexpected.
