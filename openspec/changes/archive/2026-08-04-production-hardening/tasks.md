# Tasks — production-hardening

## 1. Import model (D1)

- [x] 1.1 Delete `src/spoc/core/paths.py`; remove `inject_apps`/`eject_apps`
      wiring and `_owns_apps_path` from `Framework`
- [x] 1.2 `Framework._register_apps`: treat each app entry as a dotted path;
      derive + validate the namespace from the final segment; pass the
      namespace explicitly to the loader registration
- [x] 1.3 `Loader.register` carries an explicit `namespace` label on
      `LoadedModule`; `Framework._components_for` uses it instead of
      `entry.name.partition(".")[0]`
- [x] 1.4 `discover()` takes the namespace as a parameter instead of parsing
      it from the module name; drop the top-level-module error path
- [x] 1.5 Update kernel tests to declare apps by dotted path (test fixtures
      become packages); add the no-`sys.path`-mutation and
      no-filesystem-side-effect tests
- [x] 1.6 Scaffold: templates gain `apps/__init__.py`, config template
      declares `apps.blog`, generated entry point unchanged; update
      `tests/test_scaffold.py` and template goldens

## 2. Identity divergence (D5)

- [x] 2.1 Add `IdentityDivergenceError` to `core/exceptions.py` and the
      public `__init__` surface
- [x] 2.2 `Registry.add`: return the prior record only on identical
      identifier; raise `IdentityDivergenceError` naming both otherwise
- [x] 2.3 Tests: idempotent re-registration, divergent re-registration,
      registry unchanged after the raise

## 3. Concurrency contract (D3)

- [x] 3.1 `Registry`: one `threading.Lock` around `add` and around snapshot
      creation in every read method
- [x] 3.2 `Framework`: transition lock; sync start/shutdown acquire blocking,
      double-start check inside the lock
- [x] 3.3 Document the contract in `Registry` and `Framework` docstrings
- [x] 3.4 New `tests/test_concurrency.py`: racing starts (one winner),
      parallel distinct registrations (none lost), racing duplicate
      identifiers (one winner, loud loser)

## 4. Async lifecycle (D2)

- [x] 4.1 `Loader`: `ainitialize`/`ashutdown` coroutine variants that await
      coroutine hooks and module `initialize`/`teardown`; sync variants raise
      `SpocError` naming any coroutine they meet
- [x] 4.2 `Framework.astart`/`Framework.ashutdown`: shared sync boot phases,
      async hook dispatch, non-blocking transition-lock acquisition,
      rollback parity with the sync path
- [x] 4.3 New `tests/test_async_lifecycle.py`: async hooks awaited in order,
      sync path refuses coroutine hooks and rolls back, async shutdown
      reverse order, async rollback on failed astart

## 5. Restart honesty (D4)

- [x] 5.1 Rewrite `shutdown`/`start` docstrings: state what resets and that
      `sys.modules` + module-level state persist
- [x] 5.2 Test: start → shutdown → start with an import-time counter proving
      module code ran once and the registry rebuilt

## 6. Open mode set (D6)

- [x] 6.1 `core/config.py`: `modes` joins `SPOC_DEFAULTS`/`_SPOC_TYPES`
      (dict of list[str]); defaults hold the current triple
- [x] 6.2 `Framework._collect_apps`: consume the merged mode map instead of
      the `_MODE_CASCADE` constant; validate cascade entries and app-group
      keys against the effective set
- [x] 6.3 Tests: custom mode cascades, merge-over-defaults, unknown mode /
      unknown cascade entry fail naming the valid set

## 7. Python 3.12 floor (D7)

- [x] 7.1 `requires-python = ">=3.12"`, add the 3.12 classifier, ruff
      `target-version = "py312"` (both distributions)
- [x] 7.2 CI matrix: 3.12 / 3.13 / 3.14
- [x] 7.3 Run the full suite under uv-managed 3.12; fix anything it surfaces

## 8. Formats split (D8)

- [x] 8.1 Create `packages/spoc-formats/` with its own `pyproject.toml`
      (extras move there), `src/spoc_formats/` (moved from
      `src/spoc/formats/`, internal imports updated), and
      `tests/test_formats.py` moved in
- [x] 8.2 Root `pyproject.toml`: drop the extras, declare the uv workspace,
      dev group depends on `spoc-formats[full]` via workspace source
- [x] 8.3 Purge `spoc.formats` references from kernel docs, examples, and
      scaffold; examples import `spoc_formats`
- [x] 8.4 `release.yml`: build and publish both distributions, build both
      before publishing either

## 9. Docs, changelog, validation

- [x] 9.1 Update README quick start (dotted apps, async lifecycle, formats
      install line), docs site pages touched by D1/D2/D6/D8
- [x] 9.2 Update `docs/architecture/kernel.md` Mermaid to the post-change
      shape (paths.py gone, workspace boundary)
- [x] 9.3 CHANGELOG: breaking entries for D1/D5/D8, additions for D2/D3/D6,
      floor change for D7
- [x] 9.4 Run `.canon/checks.md` gates (ruff, ty, pytest on 3.12+3.14);
      record anything unverifiable
