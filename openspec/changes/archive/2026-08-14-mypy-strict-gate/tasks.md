# Tasks: mypy strict over `src/`

Sequencing: start only after `rename-meta-to-metadata` is applied — it edits the
declaration-layer signatures re-typed here.

## 1. Configuration (red first)

- [x] 1.1 Add `[tool.mypy]` to `pyproject.toml`: `strict = true`,
  `files = ["src/spoc"]`, `python_version = "3.12"`, `tests/conformance` excluded;
  per-module override for `spoc.core.deprecation` mirroring the ty block's comment.
- [x] 1.2 Add `types-xmltodict` to the dev group; `uv sync`.
- [x] 1.3 Run `uv run mypy` — the starting red measured 22 errors, not the ~34 in
  the design: the scoped `deprecation` escape absorbs that cluster, and annotating
  its two nested functions (missing annotations, not deliberate dynamism) removed
  more. 16 errors in 11 files were the real work.

## 2. Mechanical fixes (no behavior changes)

- [x] 2.1 Parameterize `_SubParsersAction` in the four CLI modules (scaffold,
  projection, diagnostics, stubs).
- [x] 2.2 Resolve `no-any-return` at boundaries in `formats/{operations,access,
  codecs}.py`, `scaffold/remote.py`, `stubs/extract.py` — narrow where already
  guarded, `cast` with a boundary-naming comment otherwise; add no `# type: ignore`.
- [x] 2.3 Rename the second `entry` loop variable in `Framework._boot_discovery`
  (`_AppEntry` vs `LoadedModule` reuse).
- [x] 2.4 Narrow `label` in `registrar`'s closure (`declaration.py:157`).
- [x] 2.5 Annotate the unannotated parameter in `testing/plugin.py:59`.
- [x] 2.6 Delete the redundant `src/spoc/formats/py.typed`; confirm the packaged
  root marker covers it (wheel contents unchanged otherwise).

## 3. `component()` type preservation

- [x] 3.1 Give `component()` the `@overload` pair (`obj: T → T`; bare → `Decorator`),
  reusing the existing `Decorator` protocol.
- [x] 3.2 Extend the conformance fixture with a `component()` usage so mypy, pyright,
  and ty all assert the preserved type. Two claims, both proven to fail against an
  erased marker: the parameterized value form and the bare form on a *function* — a
  decorated class proves nothing, since mypy keeps a class binding through an
  `Any`-returning decorator. The first attempt produced a real checker disagreement;
  recorded in design.md rather than suppressed. No fixture regeneration needed.

## 4. Gate wiring (three homes move together)

- [x] 4.1 `.canon/checks.md`: extend the Type checker row to `uv run ty check` +
  `uv run mypy`, with the why in the Status cell (ty is beta; mypy is the mature
  reading; disagreement is a finding, never loosened away).
- [x] 4.2 `Taskfile.yml`: same addition in the derived task.
- [x] 4.3 `.github/workflows/ci.yml`: add mypy beside ty on the full matrix.

## 5. Validation (Rule 6 — `.canon/checks.md`)

- [x] 5.1 `uv run mypy` green; `uv run ty check` still green.
- [x] 5.2 `task check` — full gate, including stub conformance (fixture may have
  been regenerated in 3.2) and apicheck/apidiff (no surface change expected beyond
  typing; `component()` overloads are compatible narrowing pre-1.0).
- [x] 5.3 Confirm exactly one `# type: ignore` remains in `src/`
  (`scaffold/remote.py:69`) plus the emitter-written stub suppression constant.
