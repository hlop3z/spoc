## 1. Build-vs-adopt gate

- [x] 1.1 Run `/ai:decide` for the critical concerns and record each ADR in `DECISIONS.md`
      — four approved: extraction (Build on stdlib), emission (Build emitter + adopt ruff),
      conformance (adopt `assert_type` under mypy/pyright/ty), IDE proof (pyright as proxy)
- [x] 1.2 Reconcile design.md with the recorded ADRs — Decision 8 rewritten, Decision 9
      added for the three-checker gate, risks extended

## 2. Generic component records

- [x] 2.1 Make `Component` generic (`class Component[T]`, `object: T`) in
      `src/spoc/core/registry.py`; confirm `Registry.add` returns `Component[Any]`
- [x] 2.2 Verify no existing annotation or call site changes meaning — bare `Component`
      still type-checks everywhere it appears in `src/`, `tests/`, and `examples/`
- [x] 2.3 Add tests covering the delta scenarios in
      `specs/component-registry/spec.md` (undescribed record unconstrained; described
      record reports its object type; runtime behavior identical)
- [x] 2.4 Confirm the type checker in CI passes on 3.12, 3.13, and 3.14 (PEP 695 syntax
      floor is 3.12 — no `typing_extensions`, no base-install dependency)

## 3. Typed accessors (no-codegen route)

- [x] 3.1 Add `resolve_type` and `resolve_object` to `Framework`, delegating to
      `Registry.resolve` so per-segment failure precision is inherited, not re-implemented
- [x] 3.2 Implement the shape check (`isinstance(obj, type)` and its negation) and a
      shape-mismatch error naming identifier, expected shape, and actual shape
- [x] 3.3 Add the new exception to the exception hierarchy and to `__all__`
- [x] 3.4 Test every scenario in `specs/typed-component-access/spec.md`, including that
      structure is deliberately *not* checked and a callable is returned uninvoked
- [x] 3.5 Add a cross-application test proving the resolving app imports nothing from the
      providing app (assert on `sys.modules` after resolution)

## 4. Describe pass

- [x] 4.1 Create the `src/spoc/stubs/` subpackage; add an import-containment test asserting
      nothing in `src/spoc/core/` or `src/spoc/framework.py` imports it
- [x] 4.2 Define the manifest IR as frozen dataclasses: per-entry identifier, shape
      (`class` | `value` | `callable`), type reference, and degraded flag
- [x] 4.3 Implement `describe(framework, base_dir) -> Manifest` reusing the existing
      collect-only sequence — discovery without `loader.initialize` and without hooks
- [x] 4.4 Implement type-reference extraction on stdlib per the ADR: `__module__`/
      `__qualname__` for classes and values, `inspect.signature` for callables
- [x] 4.5 Cover `[spoc.plugins]`-registered components explicitly — they exist only after
      configuration resolves and are the case a static extractor could not see
- [x] 4.6 Degrade to the unconstrained type when extraction cannot be faithful; count
      degraded entries on the manifest rather than guessing
- [x] 4.7 Test the describe-pass scenarios in `specs/typed-registry-stubs/spec.md`:
      initializers do not run, no residue, configuration-registered components appear,
      all three shapes distinguished, unannotated callables degrade

## 5. Stub emitter

- [x] 5.1 Implement `emit(manifest) -> str` as a pure function: `Literal` overloads on
      `resolve` in canonical identifier order, plus the trailing `str` fallback
- [x] 5.2 Emit the composition root's mirrored surface (kind handles derived from the
      declared kind set) alongside the `framework` binding
- [x] 5.3 Refuse to emit — naming the unmirrorable names — when the composition root holds
      anything beyond the framework declaration and its kind handles
- [x] 5.4 Add `--strict` to omit the fallback overload
- [x] 5.5 Apply `ruff format` to the emitted text through the file-writing adapter; keep
      `emit` itself pure
- [x] 5.6 Enable ruff's `PYI` rule family in `[tool.ruff.lint]` and confirm generated stubs
      lint clean under it
- [x] 5.7 Test that describing the same project twice is byte-identical and that
      declaration order does not perturb the output

## 6. CLI surface

- [x] 6.1 Add the `spoc stubs` verb as a thin adapter in `src/spoc/stubs/cli.py`, mirroring
      `src/spoc/diagnostics/cli.py` — argv translation and exit codes only, no logic
- [x] 6.2 Implement `--check`: regenerate in memory, diff against the stored stub, report
      match or mismatch, never write
- [x] 6.3 Make `--check` report a mismatch (not success) when no stored stub exists
- [x] 6.4 Report the degraded-entry count on both generate and check
- [x] 6.5 Test the verification scenarios in `specs/typed-registry-stubs/spec.md`:
      current stub matches, added component mismatches, missing stub mismatches, and the
      stored stub is never modified by `--check`

## 7. Runtime inertness

- [x] 7.1 Test that generating a stub for `examples/` then starting and exercising the
      project imports no cross-application modules at runtime
- [x] 7.2 Test that deleting the generated stub changes no runtime behavior

## 8. Type-checker conformance (the gate that proves the feature works)

- [x] 8.1 Add `mypy` and `pyright` to the dev dependency group alongside the existing `ty`;
      confirm the base install still declares zero runtime dependencies
- [x] 8.2 Build a fixture project covering all three component shapes, generate its stub,
      and commit both so the assertions run against a real generated artifact
- [x] 8.3 Write `typing.assert_type` assertions over the generated stub for every shape —
      `type[Product]` for a class, the call signature for a callable, the instance type for
      a value — plus one asserting a degraded entry is `Any`
- [x] 8.4 Add pyright `reveal_type(expr, expected_text=...)` assertions for the exact
      rendered type, since that string is what a VS Code hover displays
- [x] 8.5 Run mypy, pyright, and ty over the fixture in CI; a disagreement between them
      fails the build rather than being resolved by loosening the stub
- [x] 8.6 Assert that `--strict` mode makes a misspelled identifier a type error under all
      three checkers, and that permissive mode does not
- [x] 8.7 Record which checker versions were verified, so a future regression is traceable
      to a version bump
- [x] 8.8 Perform the one-time manual check in VS Code that completion actually appears on
      both the identifier string and the resolved object; document the result
      — **VERIFIED by a human, 2026-08-11.** Opening `tests/conformance/` as its own
      VS Code folder: the identifier string completes inside the quotes, hovering
      `product_cls` shows `type[Product]`, and members complete on the constructed
      object. Reproduce with the `pyrightconfig.json` in that directory, which is
      what makes `framework` resolve for Pylance. The fourth item offered in that
      walkthrough — a misspelled identifier going unflagged — is the *permissive*
      default behaving as documented, not a defect; under `--strict` pyright reports
      `No overloads for "resolve" match the provided arguments`, which
      `test_strict_mode_rejects_a_misspelled_identifier_everywhere` holds for all
      three checkers.

## 9. Docs and gates

- [x] 9.1 Write the typed-access guide: the generated route, the `Protocol` route, the
      strict/permissive tradeoff, and the composition-root constraint from Decision 3
- [x] 9.2 Document the verified type-checker support (mypy, pyright/Pylance, ty) and state
      plainly that VS Code completion is delivered through Pylance's pyright engine
- [x] 9.3 Ensure every guide example runs under `tests/test_docs_examples.py`
- [x] 9.4 Capture the new CLI help from the live parser into the tools docs section
- [x] 9.5 Add `spoc stubs --check` and the conformance job to `.canon/checks.md`, then
      propagate to `Taskfile.yml` and CI from that single source
- [x] 9.6 Confirm `apicheck` assigns a stability tier to every new public name and review
      the `apidiff` surface delta
- [x] 9.7 Update the architecture diagram in `docs/architecture/` to show `spoc.stubs`
      alongside `scaffold/`, `formats/`, and `diagnostics/` (Rule 1)
- [x] 9.8 Add the CHANGELOG entry
- [x] 9.9 Mark `docs/ideas/typed-projection.md` as partially realized, noting that the
      stub route dissolved its import-cycle open question and that the manifest and
      additional emitters remain unscheduled

## 10. Validation

- [x] 10.1 Run the full check suite from `.canon/checks.md`; report anything unrunnable as
      unverified rather than assumed passing
- [x] 10.2 Run `openspec validate add-typed-registry-access --strict`
