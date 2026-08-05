# Tasks — Error Doctrine and Hook Contract

## 1. Error doctrine: app failures propagate unwrapped

- [x] 1.1 Delete the try/except wrapper from all four lifecycle phases in
      `src/spoc/core/loader.py` (`initialize`, `ainitialize`, `shutdown`,
      `ashutdown`); kernel-authored raises inside the loops stay as they are
- [x] 1.2 Replace `tests/test_loader.py::test_startup_error_is_wrapped` with a test
      pinning that the app's own exception type and traceback propagate, with no
      `SpocError` in the chain above it; add the shutdown-hook equivalent
- [x] 1.3 Add a framework-level test: module `initialize` raising during `start`
      surfaces the app's exception and still rolls back to the inert state (both
      sync and async paths)

## 2. Hook contract: ordered, immutable payload

- [x] 2.1 Change `Framework._components_for` to return a registration-ordered
      `tuple` filtered by namespace (`src/spoc/framework.py`)
- [x] 2.2 Update payload annotations from `set[Any]` to `Sequence[Any]` on
      `KindSpec.on_startup`/`on_shutdown` (`src/spoc/core/declaration.py`) and the
      `components_for`/`KindHooks` types in `src/spoc/core/loader.py`
- [x] 2.3 Update hook tests to pin order (registration order across two starts) and
      immutability; adjust existing payload assertions in `tests/test_loader.py`,
      `tests/test_framework.py`, `tests/test_async_lifecycle.py`

## 3. Plugin identity: discovery's grammar

- [x] 3.1 Derive the plugin namespace in `Framework._register_plugins` as the
      second-to-last segment of the reference's module path (sole segment when
      top-level), validated with `validate_segment("namespace", ...)`; update the
      docstring's grammar sentence
- [x] 3.2 Add tests: deep reference under a dotted app path registers under the
      app's namespace; top-level module reference is its own namespace; existing
      two-segment plugin tests still pass unchanged

## 4. Docs, example, changelog (same change set — Rule 8)

- [x] 4.1 Update the error-doctrine wording where lifecycle errors are described:
      `docs/docs/advanced/lifecycle.md`, `docs/docs/core/loader.md`,
      `docs/docs/core/framework.md`
- [x] 4.2 Update hook-payload wording (ordered tuple, registration order) in
      `docs/docs/core/framework.md` and wherever hooks' payload is described
- [x] 4.3 Update plugin-namespace wording and examples in
      `docs/docs/advanced/plugins.md`,
      `docs/docs/getting-started/configuration.md`, and the example project /
      scaffold template comments if they state the old rule
- [x] 4.4 Fold all three breaking changes into the CHANGELOG's untagged 0.5.0
      section

## 5. Validation (Rule 6 — `.canon/checks.md`)

- [x] 5.1 Run the full gate set: pytest, ruff format/check, ty, mdlinks, mkdocs
      build; fix fallout
- [x] 5.2 `openspec validate --all` passes
