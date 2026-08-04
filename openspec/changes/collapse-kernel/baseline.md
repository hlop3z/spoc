# Baseline — measured before implementation

Captured for task 1.2 so task 9.3 can report structural and documentation reductions
separately. Structural is the figure that must clear ~446; the docstring figure must not be
allowed to flatter it.

## Totals (`tokei src/spoc --files`)

| Scope                      | Code lines |
| -------------------------- | ---------- |
| `src/spoc` (all Python)    | 2,463      |
| `src/spoc/scaffold` (out of scope) | 636 |
| **kernel in scope**        | **1,823**  |

## Kernel split (AST census, docstring lines counted as tokei counts them)

| Measure                                   | Lines |
| ----------------------------------------- | ----- |
| Kernel total                              | 1,823 |
| Inner docstrings (function/class/method)  | 629   |
| Module docstrings (kept under D8)         | 169   |
| Structural (everything else)              | 1,025 |

## Per-file, kernel only

| File                            | Code | Inner docstrings |
| ------------------------------- | ---- | ---------------- |
| `core/importer.py`              | 454  | 179              |
| `framework.py`                  | 328  | 131              |
| `core/exceptions.py`            | 168  | 57               |
| `components.py`                 | 165  | 64               |
| `core/registry.py`              | 149  | 47               |
| `core/toml_core.py`             | 101  | 40               |
| `core/config_loader.py`         | 100  | 28               |
| `core/identifier.py`            | 96   | 33               |
| `core/components_discovery.py`  | 87   | 24               |
| `case_style.py`                 | 75   | 17               |
| `__init__.py`                   | 65   | 0                |
| `inject_apps.py`                | 31   | 9                |
| `__about__.py`                  | 4    | 0                |

## Targets

| Measure    | Baseline | Target | Basis                                        |
| ---------- | -------- | ------ | -------------------------------------------- |
| Kernel     | 1,823    | ~810   | ~55% reduction                               |
| Structural | 1,025    | ~580   | ~446 removed — the figure that must hold     |
| Docstrings | 798      | ~230   | 169 module (kept) + ~60 retained one-liners  |

## Test baseline

195 tests passing before any change.
