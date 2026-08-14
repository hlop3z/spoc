# Design: mypy strict over `src/`

## Context

Today's checker layout: `ty` gates `src/` (beta, default rules); mypy 2.3.0 and
pyright 1.1.411 are pinned dev dependencies but only exercise the stub conformance
fixture (`tests/test_conformance.py`). Measured baseline: `mypy --strict src/spoc` →
34 errors / 13 files; default mode → 17 errors / 4 files. The clusters:

- 4× `type-arg` on argparse `_SubParsersAction` (`cli.py` in scaffold, projection,
  diagnostics, stubs).
- ~8× `no-any-return` where codec/OS boundaries return `Any` into a declared type
  (`formats/{operations,access,codecs}.py`, `scaffold/remote.py`, `stubs/extract.py`).
- `framework.py:587` cluster: the loop variable `entry` is reused across two loops
  with different element types (`_AppEntry`, then `LoadedModule`) — not a runtime
  bug, but a real readability defect strict mode happens to catch.
- `declaration.py:157`: `label` narrows to `str | Any | None` against a `str` param.
- `testing/plugin.py:59`: one unannotated parameter.
- `core/deprecation.py`: the PEP 702 fallback, deliberately dynamic, already carries
  a documented ty override block.
- `codecs.py:169`: `xmltodict` has no bundled types; stubs exist upstream.

## Goals / Non-Goals

**Goals:**

- `mypy --strict` green over `src/spoc` as a standing gate row, wired identically in
  checks.md, Taskfile, and CI (full platform matrix, same as ty).
- `component()` — public in `__all__` — preserves the decorated type like the kind
  handles do.
- Zero behavior changes; every fix is annotation, narrowing, or a variable rename.

**Non-Goals:**

- Not replacing ty (it stays; two independent readings, same row) and not touching
  the three-checker stub conformance gate (`typed-registry-stubs` owns it).
- Not adding pyright over `src/` — it already reads every user's editor experience
  via the conformance gate; a third src checker buys marginal signal for real CI
  cost. Revisit if mypy and ty ever disagree in a way pyright would arbitrate.
- Not chasing `Any` out of surfaces where it is the documented design
  (`Framework.objects`, `Component[Any]` from bare `resolve`, codec `decode`).

## Decisions

### Adopt, not build — and which checker

Build-vs-adopt hierarchy: mypy is adopted (already a pinned dev dependency;
reference implementation of PEP 484 checking; the most widely deployed CLI checker).
No new tool enters the project, so no new ADR is owed in `DECISIONS.md`; this block
records the scope extension. Strict mode from day one, because the measured gap (34)
is close-able in one change — adopting default mode first would ratchet twice.

### Configuration lives in `pyproject.toml`

`[tool.mypy]` beside the existing `[tool.ty]`: `strict = true`,
`files = ["src/spoc"]`, `python_version` pinned to the floor (3.12). One scoped
per-module override for `spoc.core.deprecation` mirroring the ty block's rationale
verbatim — same escape, same justification, same blast radius (one file). The
`tests/conformance/` fixture stays excluded exactly as it is for ty and ruff.

### Boundary `Any` is cast at the boundary

`no-any-return` sites take a local narrowing (`isinstance` guard) where the value is
checked anyway, or a `cast` with a one-line comment naming the boundary (stdlib API
typed `Any`, third-party codec). No `# type: ignore` — the existing count is one,
and it stays one.

### `component()` gets the handle's overload pair

`obj: T → T`; bare/keyword call → the existing `Decorator` protocol. The
`KindHandle` docstring already argues why `Any` here makes generated stubs lie; the
same argument covers the low-level marker. Verified two ways: mypy strict over the
source, and a `component()` usage added to the conformance fixture so all three
checkers assert the preserved type where users see it.

### Gate wiring follows the three-homes contract

`.canon/checks.md` Type checker row becomes `uv run ty check` + `uv run mypy` (files
pinned by config); Taskfile and CI derive from the row. The row runs on every
declared platform × interpreter — checks.md's stated reason (outcomes can differ by
platform) applies to mypy the same as ty, and mypy is cheap at 49 files.

### Recorded during apply: the first three-checker disagreement, and what it was

The conformance fixture's first `component()` claim was `assert_type(SpareIndex, type[SpareIndex])`
on a decorated class. mypy and pyright passed it; **ty rejected it** — it infers the class
object itself, a strict subtype of `type[SpareIndex]`, and `assert_type` demands
equivalence. Per the spec, a disagreement is a finding, so it was diagnosed rather than
suppressed: all three preserve the type, and the assertion was over-specified on spelling.

Probing why turned up the more useful fact. An `Any`-returning decorator leaves a *class*
binding intact under mypy, so a decorated class cannot demonstrate erasure at all — the
assertion would have passed with the defect still in place. Erasure is observable on a
decorated *function* (`untyped-decorator`, then the call degrades to `Any`) and on the
parameterized value form (`search_index` becomes `Any`). Both of those are now the claims
in the fixture, and both were verified to fail against a deliberately erased marker.

## Risks / Trade-offs

- **Two checkers, one row**: they can disagree. Treat a disagreement as a finding
  (the conformance gate already states this norm), never something to fix by
  loosening whichever checker complained.
- **mypy version drift**: the conformance gate pins mypy for stub checking; the src
  gate rides the same pin, so one bump moves both — intended, one home for the pin.
- **Strict-mode friction on future code**: new modules must be strict-clean from
  birth. Accepted; that is the point of a ratchet.
- **`types-xmltodict` staleness**: typeshed-style stubs can lag the library. Low
  risk — the codec pins `xmltodict>=1.0.4` and its API surface is one function pair.
