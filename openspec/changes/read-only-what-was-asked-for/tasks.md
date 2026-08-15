## 1. Prune the collection walk

- [ ] 1.1 Replace `_is_ignored(relative, ignore)` in `src/spoc/formats/operations.py` with a
      one-name predicate (hidden by leading dot, or matching an ignore glob), per design D3.
      Keep it private and keep the docstring stating why the question is asked per entry
      rather than per path.
- [ ] 1.2 Rewrite `collect`'s traversal as a `Path.walk()` loop that partitions each
      directory's `dirnames` with that predicate, assigns the survivors back with
      `dirnames[:] = keep`, and appends every pruned directory to `skipped` (design D1, D4).
      Apply the same predicate to `filenames`, appending skipped files as themselves.
- [ ] 1.3 Collect the surviving files into a list and sort it once before the read loop, so
      enumeration order and duplicate-reporting order are byte-identical to today (design D2).
- [ ] 1.4 Leave the body of the read loop — extension lookup, `derive_key`, the duplicate
      check, and the error wrapping — unchanged. Confirm by diff that only traversal and
      skip-recording moved.
- [ ] 1.5 Update the module docstring if it describes the traversal; it currently does not,
      so verify rather than assume.

## 2. Pin the collection's new guarantees

- [ ] 2.1 Update `tests/test_formats.py::test_ignore_patterns_extend_the_skip_set` to assert
      the ignored directory appears in `skipped` and that no file beneath it does.
- [ ] 2.2 Confirm `test_a_hidden_directory_is_skipped_not_fatal` and
      `test_a_hidden_file_is_skipped` still pass unchanged (both match on substring), and
      tighten the directory one to assert the directory's own name rather than a substring
      that a file path would also satisfy.
- [ ] 2.3 Add a test that a skipped directory is not traversed: make its contents
      unreadable or unenumerable on the running platform, and assert the collection still
      succeeds over the rest of the tree. Skip on platforms that cannot express it, using
      the suite's existing platform-conditional idiom rather than a host check.
- [ ] 2.4 Add a test pinning enumeration order over a nested fixture, so a future traversal
      change cannot shift it silently.
- [ ] 2.5 Confirm `test_skipping_happens_before_the_key_grammar_is_applied` still passes —
      pruning makes it more true, not less, since the bad segment is never derived.

## 3. Read the facet in the listing operation

- [ ] 3.1 In `src/spoc/diagnostics/core.py::list_records`, choose the reader by whether
      `kind` was given (`by_kind` versus `all`), keep the `UnknownKindError` check ahead of
      the read, filter on `namespace` only, and drop the outer `sorted` (design D5).
- [ ] 3.2 Extend the docstring to say that order comes from the registry read rather than
      being re-established here, and why narrowing costs the facet.

## 4. Pin the listing guarantees

- [ ] 4.1 Add a test in `tests/test_diagnostics.py` asserting a kind-narrowed listing
      returns records in canonical identifier order across a registry holding several kinds.
- [ ] 4.2 Confirm the existing unknown-kind test still fails with `UnknownKindError` naming
      the declared kinds, rather than returning empty.
- [ ] 4.3 Add or confirm a test that a namespace narrowing matching nothing returns empty
      rather than raising.

## 5. Validate and close out

- [ ] 5.1 Run `task check` and confirm every gate row passes; report any row that could not
      run as unverified (Rule 6).
- [ ] 5.2 Review the diff and split the commits by intent — the collection traversal and the
      listing read are two changes, not one (Rule 3).
- [ ] 5.3 Run `/opsx:sync` to fold both delta specs into the main specs, then archive with
      `openspec archive -y --skip-specs`.
