## 1. Build-vs-adopt gate

- [x] 1.1 Run `/ai:decide` and record each ADR in `DECISIONS.md` and `design.md`
      — two approved: the collision model (adopt Django's derive/fail/override contract,
      build the check) and the `as` syntax (adopt Python's convention, build the split)
- [x] 1.2 Confirm design.md's Decision 4 (reuse `ConfigurationError`) supersedes the
      proposal's sketch of a dedicated error type, and that the proposal's Impact section
      is the only place still naming one

## 2. Parsing the app entry

- [x] 2.1 Add a pure helper that splits an app entry into `(module_path, namespace)`,
      returning the derived final segment when no `as` clause is present
- [x] 2.2 Validate the stated namespace through the existing
      `validate_segment("namespace", …)` so the grammar keeps one enforcement point
- [x] 2.3 Reject a malformed entry — empty module path, empty namespace, more than one
      `as` clause — with a message naming the entry as written
- [x] 2.4 Test the parse in isolation: bare path, aliased path, surrounding whitespace,
      a module path whose segments contain the letters `as`, and each malformed form

## 3. Namespace ownership

- [x] 3.1 Build the namespace→package map from the full app list in `_register_apps`
      *before* any module is imported, so a contested namespace registers nothing
- [x] 3.2 Raise `ConfigurationError` naming the contested namespace and both declared
      paths when two distinct packages claim one namespace
- [x] 3.3 Let the same package re-claim its own namespace without error
- [x] 3.4 Consult the map in `_register_plugins`: a reference whose package differs from
      the namespace's owner fails; a reference inside the owning package succeeds
- [x] 3.5 Make a plugin reference inside an app that stated an explicit namespace register
      under the stated namespace, not the derived one
- [x] 3.6 Test every scenario in `specs/project-configuration/spec.md` and
      `specs/object-identity/spec.md`, including that a collision with no coinciding
      object name still fails

## 4. Nested-app coverage for the stub gate

- [x] 4.1 Move the conformance fixture's `shop/` under a container package so the layout
      the rule concerns is the layout the three-checker gate exercises
- [x] 4.2 Regenerate `framework.pyi` and confirm identifiers are unchanged — only the
      import paths and aliases move
- [x] 4.3 Confirm `spoc stubs --check` still reports the committed stub current, and that
      all three checkers still pass on the nested layout

## 5. Docs and gates

- [x] 5.1 Document the `as` form and the collision error where apps are declared, with
      the vendored/third-party case as the motivating example
- [x] 5.2 Ensure any new doc example runs under `tests/test_docs_examples.py`
- [x] 5.3 Confirm `apicheck` reports no new public name (the change adds none) and review
      the `apidiff` surface delta — the parse helper is `_parse_app_entry`, private by
      design; `apicheck` reports 0 fatal, and the only `apidiff` entries are the
      already-reviewed ones from the typed-access change
- [x] 5.4 Add the CHANGELOG entry, marking the behavior change as breaking

## 6. Validation

- [x] 6.1 Run the full check suite from `.canon/checks.md`; report anything unrunnable as
      unverified rather than assumed passing
- [x] 6.2 Run `openspec validate enforce-unique-namespaces --strict`
