## 1. Reproduce and pin the defect

- [x] 1.1 Add the failing conformance leg first: commit
      `tests/conformance/strict_assertions.py` (valid-identifier narrowing claims,
      readable by all three checkers) and a test that runs it against the
      ephemeral strict stub in all three checkers — confirm the mypy leg fails
      with the unsuppressed `[override]` error before any emitter change.

## 2. Fix the emitter

- [x] 2.1 Split `_STRICT_SUPPRESSION` in `src/spoc/stubs/emit.py` into its two
      placements per design D1: `# type: ignore[override]` appended to the first
      `@overload` decorator line, `# pyright: ignore[reportIncompatibleMethodOverride]`
      kept on the first signature line. Document on the constants which checker
      anchors where (D3). *(Superseded during apply: pyright turned out to report
      nothing for this narrowing, so its suppression was dropped as dead weight —
      one comment remains, mypy's, on the `@overload` line. See design D1.)*
- [x] 2.2 Handle the single-overload strict case (`len(signatures) == 1`, where the
      plain method carries the suffix and no `@overload` line exists): the
      signature is emitted pre-broken so the suppression stays pinned to the
      `def` line — verified empirically that mypy, pyright, and ty all accept it,
      since the formatter would otherwise carry a trailing comment onto the
      `...` line where mypy never reads it.
- [x] 2.3 Update the expected-output assertions in `tests/test_stubs.py` to pin the
      corrected placement, including the single-entry strict case.

## 3. Gate both emission modes

- [x] 3.1 Confirm the task 1.1 conformance leg passes in all three checkers against
      the fixed emitter's strict output.
- [x] 3.2 Add the dynamic-identifier probe per design D2: a runtime-built `str` is
      rejected by all three checkers under strict and accepted under permissive.
- [x] 3.3 Confirm every conformance failure message names the checker, and the test
      name carries the emission mode (spec scenario: checker evolution is
      detected).
- [x] 3.4 Confirm the strict path of `verify` (`spoc stubs --check --strict`) still
      matches the fixed emitter's output byte-for-byte, so a user who commits a
      strict stub gets the same staleness detection as the permissive fixture.

## 4. Validate and close out

- [x] 4.1 Run `task check` — full gate green, including the new conformance legs.
- [x] 4.2 Run `cd scripts/py && uv run apidiff ../..` and confirm an empty delta —
      this change touches no public surface.
- [x] 4.3 Verify docs need no change (suppression placement is not documented
      anywhere user-facing); note the verification in the change, per Rule 8.
