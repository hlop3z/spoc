# A mature type checker over the library source

## Why

The library's own source is gated only by `ty` — a beta checker (0.0.x) on default
rules that runs in no user's editor — while mypy and pyright, both pinned dev
dependencies, only ever check the generated-stub conformance fixture. The package
ships `py.typed` and claims `Typing :: Typed`, so its annotations are a published
contract verified by nothing mature. Measured today: `mypy --strict src/spoc` reports
34 errors in 13 of 49 files — small enough to close now, large enough to prove the
gap is real (one cluster is even a reused loop variable that obscures reading).

## What Changes

- `mypy --strict` runs over `src/spoc` as part of the Type checker gate row, beside
  `ty` — in `.canon/checks.md`, the Taskfile, and CI, on the full platform matrix.
- The 34 strict-mode findings are fixed: argparse subparser type arguments (4 CLI
  modules), `no-any-return` at codec and OS boundaries, a reused loop variable in
  `framework.py`, a label-narrowing miss in `declaration.py`, one unannotated
  parameter in `testing/plugin.py`.
- `core/deprecation.py` gets a scoped per-module override mirroring the existing ty
  override block (the PEP 702 fallback is deliberately dynamic; documented as such).
- The public `component()` marker preserves the decorated object's static type via
  the same overload pair the kind handles already have, instead of `Any → Any`.
- Type stubs for the optional XML codec's dependency are added to the dev group so
  the codec stays checked rather than ignored.
- The redundant `src/spoc/formats/py.typed` marker is removed (the package-root
  marker already covers subpackages).

## Capabilities

### New Capabilities

- `static-type-soundness`: the published source passes a mature, widely-deployed
  type checker in its strictest mode as a standing gate; public registration
  surfaces preserve the static type of what they register; deliberate dynamic
  escapes are scoped, justified in place, and enumerable.

### Modified Capabilities

_None. (`typed-registry-stubs` already owns the three-checker conformance gate for
generated stubs; that contract is untouched.)_

## Impact

- `pyproject.toml`: `[tool.mypy]` configuration, dev-group addition (type stubs for
  the XML codec dependency).
- ~13 source files with mechanical typing fixes; no behavior changes.
- `.canon/checks.md` Type checker row, `Taskfile.yml`, `.github/workflows/ci.yml` —
  the three homes that must move together.
- Sequencing: lands after `rename-meta-to-metadata`, which edits the same
  declaration-layer signatures this change re-types.
