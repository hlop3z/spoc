## 1. Build-vs-adopt gate

- [x] 1.1 Run `/ai:decide` over the six critical concerns named in `proposal.md`, recording an ADR
      per concern in `DECISIONS.md` and folding each verdict back into `design.md`
- [x] 1.2 Confirm the empty-dependency invariant holds under every recorded verdict — no published
      dependency and no required external binary — or reopen the verdict that breaks it

## 2. Reference grammar in the pure core

- [x] 2.1 Add a frozen `Reference` dataclass to `scaffold/plan.py` beside `TemplateSet`, carrying
      the resolved kind and the parsed parts
- [x] 2.2 Implement `parse_reference` in `scaffold/core.py` — total, pure, stdlib only, no I/O
- [x] 2.3 Order the discriminator so a Windows drive letter (`C:\templates`) parses as a path form
      before `:` is read as a scheme separator
- [x] 2.4 Add `UnrecognizedReferenceError` to `scaffold/errors.py`, naming the reference, the
      segment that failed, and the recognized forms — following the existing "nothing was written"
      phrasing convention
- [x] 2.5 Test the grammar as pure function calls: every recognized form, the drive-letter case,
      pin and subdirectory parts, and unrecognized input

## 3. Ports for retrieval

- [x] 3.1 Declare `RevisionResolver`, `Fetcher`, and `Cache` Protocols in `scaffold/plan.py`
      alongside `TemplateSource` and `ProjectSink`
- [x] 3.2 Split enumeration out of `TemplateSource` into an `EnumerableSource` Protocol
- [x] 3.3 Update `TemplateSetNotFoundError` to gather candidates only from enumerable sources, and
      to report recognized reference forms when the failing reference was remote
- [x] 3.4 Build in-memory fakes for all three new ports so the suite exercises remote resolution
      without a socket

## 4. Admission and bounds

- [x] 4.1 Implement member admission on the stdlib PEP 706 `filter="data"` as the primary control,
      refusing absolute paths, traversal, links, and non-regular members
- [x] 4.2 Re-verify every materialized path with the existing `resolve().is_relative_to()`
      predicate rather than adding a second one — this is the CVE-2025-4517 mitigation, not
      redundancy, since the project's interpreter floor admits unpatched versions
- [x] 4.2a Test the containment check with the extraction filter stubbed to pass everything, so
      the test exercises our defense rather than the stdlib's
- [x] 4.3 Implement the expanded-size and member-count bounds as a streaming check that stops at
      the bound, with each bound a named constant beside the concept it bounds
- [x] 4.4 Add the admission and bounds errors to `scaffold/errors.py`
- [x] 4.5 Test with crafted archives: traversing member, absolute member, common-prefix member,
      link member, expanding-beyond-bound, excessive member count

## 5. Retrieval adapter

- [x] 5.1 Implement the `Fetcher` adapter on stdlib transport in a new `scaffold/remote.py`
- [x] 5.2 Implement the redirect policy that refuses scheme downgrade
- [x] 5.3 Generate all temporary filenames locally; assert by test that no remote-supplied
      transfer metadata is read or used to build any path
- [x] 5.4 Implement `RevisionResolver` — resolve a moving reference to an exact revision before
      any content is retrieved
- [x] 5.5 Test that a redirect onto a weaker location fails, and that a hostile transfer-metadata
      name cannot place a file outside the working location

## 6. Cache adapter

- [x] 6.1 Implement the `Cache` adapter keyed by exact revision, rooted at the conventional
      platform cache directory chosen in 1.1
- [x] 6.2 Serve a retained revision without invoking the `Fetcher` at all
- [x] 6.3 Fail actionably when a revision is unretained and retrieval is unavailable, naming both
      facts
- [x] 6.4 Test cache hit, cache miss, and unavailable-retrieval behaviour against the fake ports

## 7. Resolution composition

- [x] 7.1 Replace the `if`-chain in `InstalledTemplateSources.load` with a resolver keyed on
      `Reference.kind`
- [x] 7.2 Add the remote resolver: revision → cache → fetch → admit → `load_from_directory`
- [x] 7.3 Wire the concrete adapters in `spoc/cli.py`, the existing composition root, the same way
      `derive_kinds` is injected — no new logic in `scaffold/cli.py`
- [x] 7.4 Assert by test that reference form is decided before any source is consulted, and that
      resolve-failure and load-failure are reported distinctly

## 8. Provenance

- [x] 8.1 Add the origin record to the built-in template set as a declarative data template, not a
      literal in code
- [x] 8.2 Emit it through the normal plan so it inherits never-overwrite and all-or-nothing, and
      appears in the printed file list
- [x] 8.3 Read the record in `add_app` and report divergence naming both sides, without failing
- [x] 8.4 Report "origin unknown" when the record is absent, without failing
- [x] 8.5 Test that a generated project still starts with the record deleted

## 9. Surface and documentation

- [x] 9.1 Update the `--template` help on both `init` and `app` to state the recognized forms —
      the current text describes the separator heuristic being removed
- [x] 9.2 Print the resolved revision when a moving reference was named, in a form that can be
      supplied back verbatim
- [x] 9.3 Document the reference grammar and the stated trust boundary — generation never executes
      template content, whatever its origin — in the same change set (Rule 8)
- [x] 9.4 Document that a remote reference is the only path by which the kernel performs outbound
      network access
- [x] 9.5 Execute every documentation snippet added, per the project's docs-must-run bar

## 10. Validation

- [x] 10.1 Run the checks in `.canon/checks.md`; report anything unrunnable as unverified (Rule 6)
- [x] 10.2 Assert the built wheel still declares no `Requires-Dist`
- [x] 10.3 Run the scaffold parity tests and confirm `init` and `app` still emit identical app
      shapes
- [x] 10.4 Update `docs/architecture/` with the resolution and retrieval flow (Rule 1)
- [ ] 10.5 Review the diff and split commits by intent, Conventional Commits, no co-author (Rule 3)
