## 1. Kernel — declaration surface

- [x] 1.1 Rewrite `Framework.__init__` to `Framework(*kinds, dependencies=None, mode="strict")`: pure declaration, no I/O, no `sys.path` mutation, no config loading (D1, D3)
- [x] 1.2 Implement `framework.kind(name)` returning a bare/named-form decorator; undeclared kind raises `UnknownKindError` (D2); internalize `Components` (remove from public `__init__`)
- [x] 1.3 Implement `@framework.on_ready` callback registration, and `framework.on_startup(kind)` / `framework.on_shutdown(kind)` replacing `Schema.hooks`; delete `Schema` and `Hook` from the public surface (D1, D4)

## 2. Kernel — lifecycle

- [x] 2.1 Implement `start(base_dir)`: inject apps → load `spoc.toml` → mode-cascade app list → register modules → plugins → discovery → `on_ready` callbacks → module init; double start raises; `shutdown()` before start is a no-op (D3, D4)
- [x] 2.2 Remove settings-module machinery: delete `load_configuration`, drop `Config.settings`, source `[spoc.apps]`/`[spoc.plugins]` from `spoc.toml` only; keep the `.env/<mode>.toml` cascade (D5)
- [x] 2.3 Verify the library imports standalone (no `config` package on `sys.path` required) and two `Framework` instances stay fully independent including their handles (D6, risk 1)
- [x] 2.4 Replace the hand-rolled `DependencyGraph` with stdlib `graphlib.TopologicalSorter`, translating `CycleError` to `CircularDependencyError` (cycle members preserved in the message); drop `DependencyGraph` from the public surface (ADR: dependency ordering)

## 3. Tests

- [x] 3.1 Rewrite `tests/test_framework.py` to the new surface: declaration, `kind()` handles (bare/named/undeclared), inert construction, `start`/double-start/shutdown-no-op scenarios from `framework-lifecycle` spec
- [x] 3.2 Add `on_ready` tests: fires once after discovery with the full registry, registration order, callback failure fails start
- [x] 3.3 Rewrite `tests/test_config_loader.py` for TOML-only config: only-declarative-file-consulted, missing-file defaults with warning, mode cascade, unresolvable-plugin failure scenarios from `project-configuration` spec
- [x] 3.4 Pin absence of removed API (`Components`, `Schema`, `Hook`, `load_configuration` not importable from `spoc`)

## 4. Example — definition of done

- [x] 4.1 Rewrite `examples/framework/framework.py` to the new surface (target: under 10 lines) and `examples/main.py` to declare-then-`start(BASE_DIR)`
- [x] 4.2 Reduce `examples/config/settings.py` to user-only constants; move app/plugin lists fully into `examples/config/spoc.toml`; verify `http_app.py` still projects routes untouched

## 5. Docs — one conventional path

- [x] 5.1 Rewrite quick-start and project-layout pages to the single path (declare → mark → start); delete alternative-way sections
- [x] 5.2 Rewrite configuration page: `spoc.toml` as the only kernel config, `settings.py` documented as user-owned and never read; environment cascade section updated
- [x] 5.3 Rewrite lifecycle page around construct/start/on_ready/shutdown; update API reference pages for removed and added symbols
- [x] 5.4 Update `docs/architecture/kernel.md` Mermaid diagram to the new composition (Rule 1); run the doc-link check

## 6. Validation and close-out

- [x] 6.1 Run the full `.canon/checks.md` suite (format, lint, ty, pytest, doc links) and the example end-to-end (`python main.py`, route projection)
- [x] 6.2 Commit in intent batches on the change branch (Rule 3); then `/opsx:sync` and `/opsx:archive`
