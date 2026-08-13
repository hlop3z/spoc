## Why

`spoc stubs --strict` emits output that fails one of the three checkers the project
itself names as its conformance set: mypy 2.x anchors the `[override]` diagnostic on
the `@overload` decorator line, while the emitter appends the suppression comment to
the `def` line below it, so the suppression never suppresses and every strict stub
starts life with an unsuppressed error. The gate never caught this because the
conformance suite verifies only the permissive fixture — strict mode ships unverified,
and nothing in the spec requires an emitted description to be diagnostic-free under
the checkers it exists to serve.

## What Changes

- Strict emission places each checker's suppression comment on the line where that
  checker actually anchors the diagnostic, so the emitted stub is diagnostic-free
  under every checker in the conformance set. (The corrected placement was verified
  empirically against all three checkers before this proposal.)
- The conformance suite gains a strict-mode fixture verified by the same checker set
  as the permissive one, so both emission modes are gated and a checker upgrade that
  moves a diagnostic anchor fails CI instead of failing users.
- The typed-registry-stubs spec gains the requirement this bug fell through: emitted
  output, in every emission mode, must produce no diagnostics under the project's
  conformance checkers.

Not in scope: any change to the stub API, the emission modes offered, the shape of
the overloads, or runtime behavior. The wider typed-access design exploration
(warn-mode tails, completion benchmarking) is deliberately excluded — this change
fixes the defect that exploration surfaced, nothing more.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `typed-registry-stubs`: add a requirement that a generated description MUST be free
  of type-checker diagnostics under the project's declared conformance checker set, in
  every emission mode the generator offers — verified by the conformance gate rather
  than asserted.

## Impact

- `src/spoc/stubs/emit.py` — suppression placement in strict emission (the
  `_STRICT_SUPPRESSION` handling in `_resolve_lines`).
- `tests/conformance/` — a strict fixture stub beside the permissive one, plus
  whatever wiring `tests/test_conformance.py` needs to check both modes across
  mypy, pyright, and ty.
- `tests/test_stubs.py` — expected-output assertions that pin the corrected
  suppression lines.
- No public API change, no runtime change, no docs change expected (the docs do not
  document suppression internals); `apidiff` should report an empty delta.
