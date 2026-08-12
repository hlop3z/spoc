## 1. Build-vs-adopt gate

- [x] 1.1 Run `/ai:decide` and record the ADR for the schema: JSON Schema is the adopted
      standard (Rule 9), but decide whether the schema file is hand-written or generated
      from the producer, and which draft is pinned
- [x] 1.2 Decide whether any existing vocabulary applies to a component registry, or
      whether the domain is specific enough that JSON Schema alone is the whole adoption —
      record the answer either way so it is not re-asked
- [x] 1.3 Confirm the emitter uses the standard library's JSON support directly and that
      `spoc.formats` stays uninvolved, preserving the containment boundary

## 2. The projection

- [x] 2.1 Define the projection's document shape: format version, declared kind set, and
      one entry per component with identifier, kind, namespace, object name, location, and
      shape
- [x] 2.2 Place the producer where both `spoc.stubs` and future consumers depend on it
      rather than on each other, and confirm the kernel does not import it
- [x] 2.3 Produce it from a collect-only boot, reusing the existing scope composition so
      nothing a projection run imports or registers outlives it
- [x] 2.4 Emit entries in canonical identifier order, and test that two projections of one
      unchanged project are byte-identical
- [x] 2.5 Test that reordering the installed-app list leaves the projection unchanged
- [x] 2.6 Test that a project whose startup hook raises is still describable, and that a
      discovery-time failure still fails with the kernel's own unchanged error

## 3. The schema

- [x] 3.1 Write the JSON Schema for the document and publish it with the project
- [x] 3.2 Add a test that every projection the suite produces validates against the schema,
      using whatever validator the gate in task 1.1 settled on — without adding a runtime
      dependency
- [x] 3.3 Test that a document missing a required field, or using a shape outside the
      stated vocabulary, fails validation
- [x] 3.4 State the format version in the document and test that it is independent of the
      framework's release version

## 4. Consolidating the duplicate descriptions

- [x] 4.1 Replace `stubs.manifest.Entry` and the duplicated parts of `Manifest` with the
      projection, keeping `type_ref` extraction in `spoc.stubs`
- [x] 4.2 Regenerate the conformance fixture's stub and confirm it is byte-identical to the
      committed one — this step must change no stub output
- [x] 4.3 Confirm `spoc stubs --check` still reports the committed stub current and all
      three type checkers still pass
- [x] 4.4 Test that the stub and the projection cover the same identifiers in the same order
- [x] 4.5 Review `diagnostics.RecordInfo` against the projection and record whether `spoc
      list` becomes a formatter over it now or stays as it is — design.md Decision 1 leaves
      this open deliberately, so the answer belongs in the change that closes it

## 5. The command

- [x] 5.1 Register one subcommand on the composed parser, staying a thin adapter over the
      library operation
- [x] 5.2 Write the document to standard output so it pipes, keeping diagnostics on the
      error stream
- [x] 5.3 Test that the command and the library yield the same document
- [x] 5.4 Map projection failures to the existing exit-code contract, adding no new mapping
      rule

## 6. Docs and gates

- [x] 6.1 Add the projection to `docs/architecture/kernel.md` as a surface derived from the
      registry (Rule 1)
- [x] 6.2 Document the document shape and the schema for consumers, including that it
      describes the registry as of the completion of discovery
- [x] 6.3 Ensure any new doc example runs under `tests/test_docs_examples.py`
- [x] 6.4 Assign the projection's stability tier and record that the document shape is now
      a public contract; review the `apidiff` and `apicheck` surface delta for the new
      public names
- [x] 6.5 Add the CHANGELOG entry

## 7. Validation

- [x] 7.1 Run the full check suite from `.canon/checks.md`; report anything unrunnable as
      unverified rather than assumed passing
- [x] 7.2 Run `openspec validate project-the-registry-as-data --strict`
