## 1. Subpackage skeleton and boundary

- [x] 1.1 Create `src/spoc/testing/` with `__init__.py` exporting the public names (`isolated`, `ProjectTree`, `mode`) and module stubs `core.py`, `tree.py`, `plugin.py`
- [x] 1.2 Add the containment boundary test: importing `spoc` and booting a framework never loads `spoc.testing` (mirror the existing `formats`/`scaffold` boundary tests)

## 2. Core harness

- [x] 2.1 Implement the isolation scope in `core.py` — promote the `clean_sys_path_and_modules` logic from `tests/test_framework.py` (snapshot `sys.path` + `sys.modules`, shutdown started frameworks, restore on exit including exceptional exit)
- [x] 2.2 Implement `ProjectTree` in `tree.py` — generalize `make_project` (N apps, module bodies, config entries merged into `spoc.toml`), reusing the scaffold's TOML emission rather than duplicating it
- [x] 2.3 Implement the `mode` override scope in `core.py` — rewrite `spoc.mode` in the tree's `spoc.toml` on enter, restore original bytes on exit (finally)
- [x] 2.4 Black-box tests for every spec scenario in `test-harness/spec.md` (normal exit, exceptional exit, consecutive-scope independence, plain-script usage, built tree boots, multi-app config, mode applies-and-reverts)

## 3. Pytest plugin

- [x] 3.1 Implement `plugin.py` fixtures: `spoc_tree` (builder factory over `tmp_path`) and `spoc_isolated` (isolation-scope factory) — thin adapters only
- [x] 3.2 Register `[project.entry-points.pytest11] spoc = "spoc.testing.plugin"` in `pyproject.toml`
- [x] 3.3 Tests for `pytest-integration/spec.md`: fixtures resolvable via pytester without registration, teardown runs on test failure, and importing `spoc` in a pytest-free context never loads `plugin.py` or pytest

## 4. Suite migration and cleanup

- [x] 4.1 Migrate `tests/` to `spoc.testing` where they hand-roll the same machinery; keep deliberate raw-layout tests explicit; delete the superseded helpers
- [x] 4.2 Full validation per `.canon/checks.md` (ruff, ty, pytest with coverage) — all green, coverage not regressed

## 5. Docs

- [x] 5.1 Add the "testing your app" how-to page to the mkdocs site and a README feature bullet
- [x] 5.2 Update the architecture diagram if the contained-subpackage picture changes (Rule 1/8)
