# Tasks — registry-first-kernel

## 1. Gate

- [x] 1.1 Run `/ai:decide` on the three critical concerns (object-identity, component-registry, component-resolution) — all three approved as **Build**; ADRs recorded in design.md D9 (2026-08-04)

## 2. Identity grammar (spec: object-identity)

- [x] 2.1 Add identifier module: segment regex `^[a-z][a-z0-9_]*$`, `parse(identifier) -> (kind, namespace, name)`, `compose(kind, namespace, name) -> str`, validation errors naming segment and value
- [x] 2.2 Add exceptions to `core/exceptions.py`: `MalformedIdentifierError`, `InvalidSegmentError`, `UnknownKindError`, `UnknownNamespaceError`, `UnknownObjectError`, `DuplicateComponentError` (all under `SpocError`)
- [x] 2.3 Unit tests: accept/reject matrix per segment, no-normalization proof (`MyService` fails; `case_style` is never called on the registration path)

## 3. Registry (spec: component-registry)

- [x] 3.1 Rework `Component` record: canonical `identifier` plus `kind`/`namespace`/`name` facets, object, config, metadata; delete `Internal.app_name`/`obj_name` dead fields
- [x] 3.2 Replace `Importer._components` dict-of-dicts with flat `dict[str, Component]` keyed by identifier; add facet queries (all, by kind, by namespace) with deterministic order
- [x] 3.3 Rework discovery (`_get_module_objects`): build `Component` at registration; kind/module mismatch raises naming object, kinds, and file (replaces silent `type_name == mod` filter); duplicate identifier raises
- [x] 3.4 Rework `Components.register`/`component` decorator: explicit `name=` for instances (nameless object without name raises); classes/functions default from `__name__` only when already conforming; validate kind against the schema-declared closed set; remove runtime `add_type`
- [x] 3.5 Delete `_locate_obj`, `_SKIP_NAMES`, and the `__class__`-mutation hashability block
- [x] 3.6 Unit tests: flat store facets, loud mismatch failure, duplicate rejection, instance explicit-name paths, closed kind set

## 4. Resolution (spec: component-resolution)

- [x] 4.1 Implement `Framework.resolve(identifier) -> Component`: parse, then kind → namespace → name checks, each raising its dedicated error with failing segment, value, and candidates; delete `get_component`
- [x] 4.2 Unit tests: success, each failure segment, malformed input, operation-suffix rejection, callable-returned-unexecuted

## 5. De-globalize composition (design D7)

- [x] 5.1 Delete `core/singleton.py`; make `Importer` a plain class with instance-level `module_hooks`; `Framework` constructs and owns its importer
- [x] 5.2 Delete `tests/test_singleton.py`; add test proving two `Framework` instances in one process have independent registries and hooks

## 6. Scope-line deletions (design D8)

- [x] 6.1 Delete `src/spoc/workers.py`, `src/spoc/tools.py`, `src/spoc/types.py`, `src/spoc/utils.py` and `tests/test_workers.py`, `tests/test_tools.py`
- [x] 6.2 Rewrite `src/spoc/__init__.py` exports to the surviving public API only
- [x] 6.3 Sweep for orphaned references (imports, docs links, Taskfile, examples) to the deleted modules

## 7. Examples and definition of done

- [x] 7.1 Rewrite `examples/` against the new grammar and `resolve()` (registration with conforming names, no compat views)
- [x] 7.2 Add the definition-of-done example: an HTTP app (dev-dependency only, not a kernel dependency) that generates its routes purely by enumerating the registry through the public API, importing no kernel internals; wire it as a runnable check
- [x] 7.3 Verify `pyproject.toml` still declares zero runtime dependencies; bump version to 0.4.0

## 8. Docs (design D10, Rule 8 — same change set)

- [x] 8.1 Delete `docs/docs/advanced/workers.md`, `docs/docs/api/workers.md`, `docs/docs/api/tools.md`; prune them from `mkdocs.yml` nav
- [x] 8.2 Rewrite `docs/docs/core/components.md`, `core/framework.md`, `core/importer.md`, getting-started pages, and example pages against the new grammar, registry, and resolve() (no page may teach the dead `app_object` URI or `get_component`)
- [x] 8.3 Reposition `README.md`: registry-first kernel under any HTTP surface, identifier grammar, quick-start with `resolve()`
- [x] 8.4 Add `docs/architecture/` Mermaid diagram: surfaces → kernel (registry) ← apps, dependencies pointing inward (Rule 1)

## 9. Validation and close-out

- [x] 9.1 Fill `.canon/checks.md` rows now that they exist: unit tests (`uv run pytest tests/`), linter (`uv run ruff check`), type checker (`uv run ty check`); fix the pre-existing `test_tools.py` Optional/Union failure by deletion (module removed in 6.1)
- [x] 9.2 Run all checks in `.canon/checks.md`; report anything unrunnable as unverified (Rule 6)
- [x] 9.3 Review the full diff, split into intent-sized Conventional Commits (Rule 3)
