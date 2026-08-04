## 1. Gates before any code

- [ ] 1.1 Run `/ai:decide` for the three concerns in design.md D5 (project generation, CLI
      surface, filesystem write safety); record each as an ADR in `DECISIONS.md` and replace
      the D5 leaning table with the decided outcomes
- [ ] 1.2 Resolve open question 1 — whether resolving the framework declaration imports the
      module — and record the answer in design.md D4
- [ ] 1.3 Resolve open questions 2 and 3 (init generates one app or none; how a downstream
      template set is referenced) and record them in design.md
- [ ] 1.4 Confirm the adopted generator can emit into an existing project (the `add app` case);
      if it cannot, record the adopt-for-init / build-narrow-in-place split explicitly

## 2. Core — pure, no I/O

- [ ] 2.1 Define the generation plan type: ordered (relative path, content) pairs plus the
      config edits an operation implies, immutable once built
- [ ] 2.2 Define the `TemplateSource` and `ProjectSink` ports in the core; assert by test that
      the core module imports nothing outside the standard library and the kernel
- [ ] 2.3 Implement name validation against the kernel's existing identity grammar, reusing
      `validate_segment` rather than restating the pattern
- [ ] 2.4 Implement path-traversal rejection for user-supplied names, verified against a target
      directory boundary
- [ ] 2.5 Implement template set validation: required elements present, declared substitution
      values all satisfiable, failing with the missing element named
- [ ] 2.6 Implement plan construction for `init` — configuration file, framework declaration,
      one app per declared kind set, entry point — with all names agreeing by construction
- [ ] 2.7 Implement plan construction for `add app`, including the config edit that registers
      the app under the selected mode (defaulting to development)
- [ ] 2.8 Implement conflict detection as a pure comparison between a plan and a supplied
      directory listing

## 3. Adapters

- [ ] 3.1 Implement the template source adapter that loads a template set directory and its
      manifest
- [ ] 3.2 Implement built-in template set resolution plus downstream set resolution per the
      decision from 1.3, failing with candidates listed when unresolvable
- [ ] 3.3 Implement the project sink: stage, verify, commit, so a failure leaves no partially
      written files
- [ ] 3.4 Implement the framework-declaration reader per the decision from 1.2, so `add app`
      emits one module per kind the target project declares
- [ ] 3.5 Implement the config editor that registers an app under a mode while preserving the
      existing file's comments and ordering

## 4. Command surface

- [ ] 4.1 Build the CLI entry point over the core operations, carrying no generation logic
- [ ] 4.2 Wire `init` and `add app` subcommands with their arguments, including template set
      selection and mode selection
- [ ] 4.3 Render refusals as messages that name the conflicting path, the offending value, or
      the missing element, matching what the specs require each failure to name

## 5. Distribution

- [ ] 5.1 Add the opt-in extra and console entry point; verify `dependencies = []` in
      `pyproject.toml` is unchanged
- [ ] 5.2 Add a test asserting the kernel imports nothing from the scaffolder package, so the
      dependency runs one way only
- [ ] 5.3 Verify a kernel install without the extra acquires no scaffolding dependency and
      starts a project normally

## 6. Verification

- [ ] 6.1 Write the round-trip test from design.md D6: generate into a temporary directory,
      start the framework, assert registry contents, shut down
- [ ] 6.2 Cover every spec scenario in `project-scaffolding` as a test, including each refusal
      path and the partial-write guarantee
- [ ] 6.3 Cover every spec scenario in `scaffold-templates` as a test, including a downstream
      template set and the not-executed guarantee
- [ ] 6.4 Run the full `.canon/checks.md` suite and confirm CI passes

## 7. Documentation

- [ ] 7.1 Lead the getting-started path with the generated project; keep hand-assembly as the
      explanation of what was generated, not as the first instruction
- [ ] 7.2 Document the scaffolder-side convention from D4 explicitly as the scaffolder's, not
      the kernel's
- [ ] 7.3 Document how a downstream framework supplies its own template set
- [ ] 7.4 Update the architecture diagram in `docs/architecture/` to show the scaffolder as a
      surface over the core, with the inward-only dependency direction visible (Rule 1)
