# Results — measured after implementation

Task 9.3. Structural and documentation reductions are reported separately, as design D8
and the risk register require, so neither flatters the other.

## Headline

| Measure                    | Baseline | Now   | Δ            |
| -------------------------- | -------- | ----- | ------------ |
| `src/spoc` (all Python)    | 2,463    | 1,614 | **−34%**     |
| `src/spoc/scaffold` (out of scope) | 636 | 636 | 0            |
| **kernel**                 | 1,823    | 978   | **−46%**     |
| — structural               | 1,025    | 770   | −25% (−255)  |
| — docstrings               | 798      | 208   | −74% (−590)  |
| kernel modules             | 14       | 11    | −3           |
| tests (lines)              | 1,557    | 1,569 | +12          |
| tests (count)              | 195      | 209   | **+14**      |

## Per-module

| Before                                       | After                | Δ    |
| -------------------------------------------- | -------------------- | ---- |
| `core/importer.py` 455                        | `core/loader.py` 134 | −321 |
| `framework.py` 328                            | `framework.py` 176   | −152 |
| `components.py` 168 + `components_discovery.py` 87 | `core/declaration.py` 140 | −115 |
| `core/identifier.py` 96 + `case_style.py` 75  | `core/identity.py` 80 | −91  |
| `core/config_loader.py` 100 + `core/toml_core.py` 101 | `core/config.py` 112 | −89  |
| `core/registry.py` 149                        | `core/registry.py` 113 | −36 |
| `core/exceptions.py` 168                      | `core/exceptions.py` 140 | −28 |
| `inject_apps.py` 31                           | `core/paths.py` 21   | −10  |
| `__init__.py` 65                              | `__init__.py` 58     | −7   |

## Where this missed the target, and why

The design set the structural figure as the one that had to hold: **~446 lines removed**.
It came in at **255**. That is a real miss, not a rounding difference, and it is the honest
headline of this section.

Two causes, both identifiable:

1. **The change added capability that did not exist at baseline.** `KindSpec`, the metadata
   contract and its checker, the absent-versus-broken discrimination, and two new error
   classes are together roughly **+80 lines** of logic with no predecessor to subtract from.
   The design counted only removals and never budgeted for the additions the same change was
   making.
2. **The exceptions estimate assumed a collapse that invariant 5 forbids.** The projection
   was 111 → 55 post-docstring. Every class had to stay independently catchable for
   per-segment precise failure, so only the docstrings and the attribute assignments
   compressed — and two classes were added. Actual: −28 against a predicted −56.

The docstring reduction overshot (−590 against a projected ~570), which is why the kernel
total still landed near the projection while the structural half did not. That is exactly
the flattering effect the separate reporting was introduced to expose.

## What did land as designed

- The dependency inversion is gone: the loader is 321 lines lighter and has never seen a
  registry. That single change is 38% of the entire reduction.
- Both deferred API items shipped as `KindSpec` fields rather than parameters threaded
  through five layers — the argument for doing this as one change.
- Test count rose 195 → 209 while test lines rose only 12, so coverage grew rather than
  shrank. Deleted tests went with the API they covered; none was deleted for failing.

## Verification

All commands from `.canon/checks.md`, run green:

| Check         | Command                                | Result           |
| ------------- | -------------------------------------- | ---------------- |
| Formatter     | `uv run ruff format --check .`          | 50 files clean   |
| Linter        | `uv run ruff check`                     | passed           |
| Linter (Go)   | `go vet ./...`                          | passed           |
| Type checker  | `uv run ty check`                       | passed           |
| Unit tests    | `uv run pytest`                         | 209 passed       |
| Doc links     | `uv run mdlinks ../..`                  | no broken links  |
| Docs site     | `uv run mkdocs build --strict`          | built clean      |
| Wheel         | `uv build --wheel` + METADATA inspection | no `Requires-Dist`, no `Provides-Extra` |

`test_generated_project_starts_unedited` passes, which resolves the scaffolder open
question: the generated `spoc.Framework("models", "views")` is still valid under the
bare-string shorthand, and both kinds register.
