## 1. Gate and baseline

- [x] 1.1 Run `/ai:decide` on the configuration-validation concern (design D7) and record the ADR in `DECISIONS.md` — settled: build-minimal on stdlib for config, `ty` plus a one-line boundary check for metadata (design D4). Section 5 is unblocked
- [x] 1.2 Record the baseline with `tokei src/spoc --files`, split into structural and docstring lines, and note it in this change directory so the completion report can compare against it — see `baseline.md`
- [x] 1.3 Inventory every `:::` directive in `docs/docs/api/*.md` against the symbols this change deletes, producing the list section 8 must action — see `docs-inventory.md` (39 directives)

## 2. Core — identity and registry

- [x] 2.1 Reduce `case_style` to the single conversion the kernel uses, deleting the other converters, the style dispatcher, and the type guard — merged into `core/identity.py`, since name derivation *is* identity
- [x] 2.2 Apply the docstring policy (design D8) to the identity module, keeping its module docstring and removing per-function Args/Returns/Raises blocks
- [x] 2.3 Rebuild the error family on a shared structured base with per-class templates, preserving every user-visible message string verbatim (design D5) — including the base's trailing-space format
- [x] 2.4 Move discovery into core: it takes a loaded module and a registry, and no longer reaches into a loader cache — now `declaration.discover()`
- [x] 2.5 Make `Registry` self-owned — constructed from the declaration, not by the loader — and apply the docstring policy to it
- [x] 2.6 Run the suite; identity, registry, and discovery must pass with no loader present — verified by a standalone smoke run importing no loader

## 3. Core — declaration and `KindSpec`

- [x] 3.1 Introduce `KindSpec(name, depends_on, required, metadata, on_startup, on_shutdown)` as the single per-kind record (design D2)
- [x] 3.2 Accept a bare kind name as shorthand that expands to a default `KindSpec` (design D10 trade-off) — `as_kind_spec()`
- [x] 3.3 Delete the `Components` class; keep the marker attach/read functions, with the kind-set check happening exactly once
- [x] 3.4 Stop carrying the kind inside the metadata mapping under a string key; make it a field checked directly against the module's location — `Internal.kind`
- [x] 3.5 Implement the per-kind metadata contract: a stated type is checked at registration, and a kind stating no contract accepts no metadata
- [x] 3.6 Verify the delta spec scenarios in `specs/framework-declaration/` and `specs/component-registry/` are covered by tests — `TestKindSpec`, `TestMetadataContract`, `test_no_second_free_form_channel`

## 4. Adapters — loader

- [x] 4.1 Make the loader kind-blind: it loads named modules in dependency order and reports each module's kind without interpreting it — the kind is an opaque label carried in and back out
- [x] 4.2 Delete the never-read `on_startup_name`/`on_shutdown_name` options and the `ModuleInfo` fields that exist only to receive them
- [x] 4.3 Delete the empty `on_startup`/`on_shutdown` subclass extension points
- [x] 4.4 Delete the cache and unload operations reachable only from their own tests, and the convenience wrapper the framework never calls
- [x] 4.5 Replace the pattern-matching hook machinery with a per-kind lookup, deleting the hook containers, the wildcard-to-regex helper, and the generic/pattern split (design D6)
- [x] 4.6 Reduce `ModuleInfo` to a dataclass — now `LoadedModule`
- [x] 4.7 Implement per-kind optionality: a missing module consults its own kind's `required` field, and a module that exists but raises on import is an error regardless (design D3) — absent vs broken told apart by `ModuleNotFoundError.name`
- [x] 4.8 Verify the delta spec scenarios in `specs/framework-lifecycle/` are covered by tests, including that optionality does not leak between kinds — `TestAbsentVersusBroken` plus four framework-level tests

## 5. Adapters — configuration

- [x] 5.1 Implement the configuration-validation decision from task 1.1 — four explicit checks; the recursive schema engine is deleted
- [x] 5.2 Apply the docstring policy to the configuration and path-injection modules

## 6. Composition root

- [x] 6.1 Rewire `Framework` to own the registry, the loader, and the config adapter directly, deleting the private forwarding methods that existed to reach through the loader
- [x] 6.2 Drive dependency order, hooks, and optionality from the `KindSpec` sequence rather than parallel dictionaries
- [x] 6.3 Delete the framework-wide strict/loose switch outright
- [x] 6.4 Apply the docstring policy to `Framework`
- [x] 6.5 Confirm construction is still inert and two instances in one process still share nothing — `test_construction_is_inert`, `test_two_frameworks_are_independent`

## 7. Public surface

- [x] 7.1 Reduce the export list to the framework author's surface, removing cache manipulation, the deleted conversion utilities, and internal declaration machinery (design D10)
- [x] 7.2 Resolve the open question on whether the loader stays public, and record the answer in `design.md` — it does not; recorded under D1

## 8. Documentation

- [x] 8.1 Update `docs/docs/api/*.md` for every symbol deleted in sections 2-7, using the inventory from task 1.3 — all 39 directives actioned; nav labels updated to Loader/Declaration
- [x] 8.2 Update `docs/architecture/kernel.md` so the diagram shows the four-module shape and the inward-only dependency direction — plus new KindSpec and absent-vs-broken diagrams, and three added invariants
- [x] 8.3 Update any getting-started or guide page that shows the framework-wide strict/loose switch or the untyped configuration channel — 8 guide pages
- [x] 8.4 Run `mkdocs build --strict` and fix every unresolved reference — built clean; one wrong anchor fixed

## 9. Validation and reporting

- [x] 9.1 Classify every failing test as covering removed API (delete with it) or surviving behavior (port it); delete no test merely because it fails — see `results.md`; 195 → 209 tests
- [x] 9.2 Run the full `.canon/checks.md` suite green — every row, including `go vet`, doc links, and the strict docs build
- [x] 9.3 Re-measure with `tokei` and report structural and docstring reductions separately against the task 1.2 baseline — see `results.md`. **Structural target missed: −255 against a projected −446**, cause identified
- [x] 9.4 Confirm the built wheel still declares no runtime dependencies — no `Requires-Dist`, no `Provides-Extra`
- [x] 9.5 Check the scaffolder's generated project still starts unedited, resolving the open question in `design.md` — `test_generated_project_starts_unedited` passes
