## 1. Gates before any code

- [x] 1.1 Run `/ai:decide` for the concerns in design.md D5; record each as an ADR — decided:
      generation, CLI, and write safety all Build-thin on the standard library
- [x] 1.2 Resolve the open questions in design.md — all three closed, two of them dissolved by
      the scope cut
- [x] 1.3 Narrow scope to `init` only; drop `add app` and reconcile proposal, specs, and design
- [ ] 1.4 Fold the D5 ADRs into `DECISIONS.md` on archive, so the project-wide record carries
      the stdlib-over-cyclopts reasoning for shipped surfaces

## 2. Core — pure, no I/O

- [x] 2.1 Define the generation plan type: ordered (relative path, content) pairs, immutable
      once built
- [x] 2.2 Define the `TemplateSource` and `ProjectSink` ports; assert by test that the core
      module imports nothing outside the standard library and the kernel
- [x] 2.3 Implement name validation against the kernel's existing identity grammar, reusing
      `validate_segment` rather than restating the pattern
- [x] 2.4 Implement path-traversal rejection via `Path.resolve().is_relative_to()` against the
      target directory boundary
- [x] 2.5 Implement template set validation: required elements present, and every identifier
      reported by `Template.get_identifiers()` satisfiable from the supplied values
- [x] 2.6 Implement plan construction for `init` — configuration file, framework declaration,
      one app with a module per declared kind, entry point — names agreeing by construction
- [x] 2.7 Implement conflict detection as a pure comparison between a plan and a supplied
      directory listing

## 3. Adapters

- [x] 3.1 Implement the template source adapter that loads a template set directory and its
      manifest, stripping the template suffix on emit
- [x] 3.2 Implement built-in template set resolution plus downstream resolution by installed
      entry point, failing with candidates listed when unresolvable
- [x] 3.3 Implement the project sink: stage into a temporary directory, verify, then commit
      with `os.replace`, so a failure leaves no partially written files

## 4. Command surface

- [x] 4.1 Build the `argparse` entry point over the core operation, carrying no generation logic
- [x] 4.2 Wire the `init` command and its arguments, including template set selection
- [x] 4.3 Render refusals as messages that name the conflicting path, the offending value, or
      the missing element, matching what the specs require each failure to name

## 5. Distribution

- [x] 5.1 Add the console entry point; verify `dependencies = []` in `pyproject.toml` is
      unchanged and no extra was introduced
- [x] 5.2 Add a test asserting the kernel imports nothing from the scaffolder package, so the
      dependency runs one way only

## 6. Verification

- [x] 6.1 Write the round-trip test from design.md D6: generate into a temporary directory,
      start the framework, assert registry contents, shut down
- [x] 6.2 Cover every spec scenario in `project-scaffolding` as a test, including each refusal
      path and the partial-write guarantee
- [x] 6.3 Cover every spec scenario in `scaffold-templates` as a test, including a downstream
      template set and the not-executed guarantee
- [x] 6.4 Confirm the template files are excluded from ruff and ty, and that excluding them
      does not hide the emitted project from the round-trip test
- [ ] 6.5 Run the full `.canon/checks.md` suite and confirm CI passes

## 7. Documentation

- [ ] 7.1 Lead the getting-started path with `spoc init`; keep hand-assembly as the explanation
      of what was generated, not as the first instruction
- [ ] 7.2 Document adding a second app by hand, pointing at the generated app as the example —
      this is the DX the `add app` cut depends on being adequate
- [ ] 7.3 Document how a downstream framework supplies its own template set
- [ ] 7.4 Update the architecture diagram in `docs/architecture/` to show the scaffolder as a
      surface over the core, with the inward-only dependency direction visible (Rule 1)
