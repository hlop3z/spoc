## Context

The stub emitter (`src/spoc/stubs/emit.py`) is a pure core function: manifest in, stub
text out. Strict mode drops the trailing `str` overload from the narrowed `resolve`,
which makes the override incompatible with `Framework.resolve` under the LSP, so the
emitter appends suppression comments. Today both suppressions ride the first overload's
`def` line:

```
    @overload
    def resolve(  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
```

A scratchpad spike (2026-08-13, three-checker matrix over hand-built stub variants)
established the facts this design rests on:

- **pyright 1.1.411** anchors `reportIncompatibleMethodOverride` such that the `def`-line
  suppression works — strict output is clean today.
- **mypy 2.3.0** anchors `[override]` on the `@overload` decorator line above, so the
  `def`-line `# type: ignore[override]` never applies and strict output fails with an
  unsuppressed error.
- **ty 0.0.66** reports no override incompatibility on this pattern; it needs no
  suppression either way.
- Moving mypy's comment to the `@overload` line while leaving pyright's on the `def`
  line passes all three checkers.

The conformance suite (`tests/test_conformance.py` + `tests/conformance/`) runs mypy,
pyright, and ty over one committed fixture stub — the permissive one. Strict emission
has unit tests asserting its text (`tests/test_stubs.py`) but no checker ever reads its
output in CI, which is exactly how a mis-anchored suppression shipped.

## Goals / Non-Goals

**Goals:**

- Strict emission produces output that is diagnostic-free under all three conformance
  checkers at their pinned-or-newer versions.
- Both emission modes are gated by the conformance suite, so a checker upgrade that
  moves a diagnostic anchor is caught in CI.
- The suppression placement is pinned by unit test, so the emitter cannot silently
  regress to a placement no checker honors.

**Non-Goals:**

- No new emission mode (the warn-mode/deprecated-tail idea from the same exploration is
  a separate, future change).
- No change to overload shape, stub API, CLI flags, or runtime behavior.
- No attempt to make ty require a suppression it does not ask for.

## Decisions

### D1 — One suppression, on mypy's anchor line; none for checkers that report nothing

The emitter writes a single suppression — mypy's — on the line where mypy anchors
`[override]`: the first `@overload` decorator, or, in the single-entry case (no
decorator line exists), pinned to the `def` line by emitting that signature pre-broken
so the formatter cannot carry the comment onto the `...` line:

```
    @overload  # type: ignore[override]
    def resolve(
```

**Why:** a checker honors a suppression only on the line where it anchors the
diagnostic. During apply, an empirical probe (strict stub with the pyright comment
stripped) showed pyright 1.1.411 reports nothing for this narrowing at all — the
shipped pyright suppression was dead weight, and after formatting it landed on the
`...` line where it could not have worked even if needed. ty reports nothing either.
A comment no checker reads is a claim the conformance gate cannot verify, and pyright
flags unused ignores under `reportUnnecessaryTypeIgnoreComment`, so dead suppressions
are actively harmful. A checker that *starts* reporting fails the new strict
conformance leg — that is the detection point, not a defensive comment.

**Alternatives considered:**
- *Split suppressions across both anchor lines (mypy on `@overload`, pyright on
  `def`).* The original plan; dropped when the probe showed pyright has nothing to
  suppress.
- *One combined comment on the `@overload` line.* Rejected for the same reason plus
  the dead-weight objection.
- *`mypy: disable-error-code` file-level pragma.* Rejected: it would suppress
  `[override]` for the entire stub, wider than the one deliberate narrowing.
- *Restructure to avoid the LSP violation entirely (e.g., not subclassing
  `Framework`).* Rejected here: that changes the stub's shape and belongs to the wider
  typed-access exploration, not a defect fix.

### D2 — Gate strict mode through the existing ephemeral conformance path

Stub storage is one path per composition root (`stub_path` — the root file with
`.pyi`), so there is no place to commit a second, differently-named strict stub, and
inventing a parallel storage convention is out of scope for a defect fix. The
conformance suite already generates a strict stub ephemerally (a tmp copy of the
fixture project + `generate(strict=True)`), but only asserts that a *typo* probe fails
— which mypy satisfied for the wrong reason, the stub's own unsuppressed error. The
missing leg is the complement: a committed `strict_assertions.py` (valid-identifier
narrowing claims, readable by all three checkers) runs against the ephemeral strict
stub and MUST pass cleanly, and a dynamic-`str` probe is rejected under strict and
accepted under permissive.

**Why:** determinism of strict output is already pinned by unit test, so an ephemeral
stub is byte-identical to what a user's `spoc stubs --strict` writes; what conformance
must add is checker *acceptance*, and the ephemeral path tests exactly the artifact a
user gets.

**Alternatives considered:**
- *Assert strict text only in unit tests.* Rejected: that is the arrangement that
  shipped the bug — text assertions pin what we *believe* checkers want.
- *A committed `framework_strict.pyi` beside the permissive stub.* Rejected during
  apply: it has no home in the one-path-per-root storage model, `verify` could never
  check it without a second path convention, and its module name would match no real
  module.
- *A second fixture project.* Rejected: same project, second emission mode; a second
  project would test nothing new and double the maintenance surface.

### D3 — Record the checker-anchor contract as a comment on the constant, not config

The corrected placement is knowledge about *external tools'* diagnostic anchoring. It
stays a documented constant in the emitter (`_STRICT_SUPPRESSION` splitting into its
two placements) with a comment naming which checker reads which line and why — not a
config value, because no user has a reason to move a suppression to a line where the
checker cannot see it.

**Alternatives considered:** making placement configurable. Rejected: configuration
whose only wrong values are silently broken is a trap, not flexibility.

### Build-vs-adopt

No new dependency and no critical concern with a build-vs-adopt fork: the change
corrects text emitted for already-adopted tools (mypy, pyright, ty — adopted by the
existing conformance row in `.canon/checks.md`). Nothing to record via `/ai:decide`.

## Risks / Trade-offs

- **[Checker drift]** A future mypy or pyright release moves its anchor line again →
  the strict conformance fixture now fails CI the day the pinned version advances,
  which is the detection this change exists to add. The unit test pins our placement;
  the conformance run pins its acceptance.
- **[pyright or ty starts reporting]** either checker later implements or re-enables
  override narrowing checks → the strict conformance leg fails in CI; the fix is adding
  a suppression on that checker's anchor line, localized to the same constant.
  Accepted: unpredictable, cheap to absorb, and detected the day it happens.
- **[Suppression breadth]** `# type: ignore[override]` on the `@overload` line could in
  principle mask a different `[override]` error on that same line. Accepted: the line
  carries only the decorator; the narrowing it suppresses is the one the strict mode
  deliberately makes.
