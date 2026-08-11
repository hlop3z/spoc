# Starter Layer — Tasks

## 1. Build-vs-adopt gate (before any implementation)

- [x] 1.1 Run `/ai:decide` for the starter's surface stack — **decided 2026-08-10:
      surface-neutral**; stdlib command surface, transport bindings as runnable docs
      recipes; Decision block recorded under design ADR-5
- [x] 1.2 Run `/ai:decide` for the documented settings-validation seam — **decided
      2026-08-10: tool-agnostic contract, plain pydantic as the worked example**;
      Decision block recorded under design ADR-3

## 2. Config passthrough (spec: project-configuration)

- [x] 2.1 Keep non-`spoc` top-level tables in `load_spoc_toml` and expose them on the
      `Config` record (new frozen field; deep-copied per load), leaving `[spoc]`
      validation untouched
- [x] 2.2 Tests: app-owned table reachable through `framework.config`; not validated;
      isolated across loads; `[spoc]` closed-set behavior unchanged
- [x] 2.3 Update `docs/docs/getting-started/configuration.md`: the one-claimed-table
      contract, app-owned tables, and the settings-validation seam (naming the 1.2
      adopted recommendation; pydantic pinned in the examples group so the snippet
      test runs)

## 3. Kind vocabulary (spec: kind-vocabulary)

- [x] 3.1 Write the vocabulary page in `docs/docs/learn/`: the five kinds, meanings,
      lifecycle roles, and the deviation rule in one authoritative table
      (`learn/vocabulary.md`, added to nav)
- [x] 3.2 Write the resource-lifecycle recipe (open via kind `on_startup`, reach via
      `resolve`, close via `on_shutdown`) with a runnable snippet — mirrored
      executable in `test_resource_lifecycle_recipe_from_the_vocabulary_page`
- [x] 3.3 Cross-check every vocabulary mention in existing docs and templates for
      agreement with the new page — no conflicts; storefront's `middleware` is a
      sanctioned deviation, taught under no competing meaning

## 4. Reference application demonstrates resources (spec: reference-application)

- [x] 4.1 Add a `resources` kind and one process-lifetime resource to the storefront
      (`catalog/resources.py` SearchIndex; opened by kind hook, resolved by
      `views:catalog.find_product` mid-call, closed at shutdown; async twin gets
      coroutine hooks)
- [x] 4.2 Extend `tests/test_examples.py` to observe both the open and the release —
      9 passed, including `spoc check` over the reference project; `examples.md`
      updated in the same change set (Rule 8)

## 5. Starter template set (spec: starter-templates)

- [x] 5.1 Author the starter set under `src/spoc/scaffold/templates/starter/` — 12
      templates + manifest, fully concrete (no per_kind: substitution cannot express
      the resources hook wiring), values = {project_name, app_name}
- [x] 5.2 Register via `BUILTIN_SETS` beside `BUILTIN_SET` in `sources.py` — same
      resolution path, four-line generalization
- [x] 5.3 Added `template-set:starter` as **provisional** in `[tool.spoc.stability]`
      (settles after a full minor line unchanged); apicheck 0 fatal, apidiff clean
- [x] 5.4 `tests/test_scaffold_starter.py`: 6 tests — resolve-by-name, boot with full
      vocabulary + resource open/release, projection↔registry one-to-one, add-a-command
      extends CLI without surface edits, end-to-end subprocess run, AST import scan
- [x] 5.5 Kernel `dependencies = []` untouched; AST scan proves every generated import
      is stdlib/spoc/project-local — full suite 651 passed

## 6. Docs, diagrams, and closure

- [x] 6.1 Starter walkthrough page (`getting-started/starter.md`, in nav) with the
      HTTP binding recipe executed in `test_http_binding_recipe_from_the_starter_page_runs`;
      messaging/worker variants described as shapes over the same table
- [x] 6.2 Updated `docs/architecture/scaffold-resolution.md` — built-in sets node now
      enumerates `default · starter`, with the fully-concrete rationale
- [x] 6.3 Full `task check` green: format, lint, types, 652 package tests, 111 tool
      tests, mdlinks, apicheck (0 fatal), apidiff (clean); CHANGELOG Unreleased added
- [x] 6.4 ADR-4 reads as closed — reopening requires an actual third-party package
      that needs kind contribution, not an archived question
- [x] 6.5 Both `/ai:decide` Decision blocks promoted into `DECISIONS.md` in its ADR
      shape
