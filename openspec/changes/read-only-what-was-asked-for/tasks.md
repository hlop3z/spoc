## 1. Prune the collection walk

- [x] 1.1 Replace `_is_ignored(relative, ignore)` in `src/spoc/formats/operations.py` with a
      one-name predicate (hidden by leading dot, or matching an ignore glob), per design D3.
      Keep it private and keep the docstring stating why the question is asked per entry
      rather than per path.
- [x] 1.2 Rewrite `collect`'s traversal as a `Path.walk()` loop that partitions each
      directory's `dirnames` with that predicate, assigns the survivors back with
      `dirnames[:] = keep`, and appends every pruned directory to `skipped` (design D1, D4).
      Apply the same predicate to `filenames`, appending skipped files as themselves.
- [x] 1.3 Collect the surviving files into a list and sort it once before the read loop, so
      enumeration order and duplicate-reporting order are byte-identical to today (design D2).
- [x] 1.4 Leave the body of the read loop — extension lookup, `derive_key`, the duplicate
      check, and the error wrapping — unchanged. Confirm by diff that only traversal and
      skip-recording moved.
- [x] 1.5 Update the module docstring if it describes the traversal; it currently does not,
      so verify rather than assume. **Verified: it describes eagerness only. No change.**
- [x] 1.6 (added during apply) Sort the skipped set before returning. A walk yields entries
      in filesystem order, which differs between machines; the whole-tree sort this change
      replaces made the report reproducible without anyone stating it. Ordering a set that
      is a set by contract is free, and losing reproducibility silently would not be.

## 2. Pin the collection's new guarantees

- [x] 2.1 Update `tests/test_formats.py::test_ignore_patterns_extend_the_skip_set` to assert
      the ignored directory appears in `skipped` and that no file beneath it does.
- [x] 2.2 Confirm `test_a_hidden_directory_is_skipped_not_fatal` and
      `test_a_hidden_file_is_skipped` still pass unchanged (both match on substring), and
      tighten the directory one to assert the directory's own name rather than a substring
      that a file path would also satisfy.
- [x] 2.3 ~~Add a test that a skipped directory is not traversed via unreadable contents,
      skipping on platforms that cannot express it.~~ **Superseded during apply.** The
      scenario does not discriminate: `Path.walk` defaults to `on_error=None` and `rglob`
      also swallows `OSError`, so an unreadable skipped directory yields an identical
      successful collection under both implementations. It would also have been the suite's
      first host-conditional test, which `platform-support` forbids ("selected by value
      rather than by the host"). Replaced with
      `test_a_skipped_directory_reports_as_one_entry_whatever_it_holds`, which pins the
      observable half — the skipped set does not grow with the tree it was told to skip.
      The delta spec was corrected to match; see the note under group 6.
- [x] 2.4 Add a test pinning enumeration order over a nested fixture, so a future traversal
      change cannot shift it silently. **Two tests**: one asserting order equals a whole-tree
      path sort (and pinning that as a value), one asserting pruning does not reorder what
      survives it.
- [x] 2.5 Confirm `test_skipping_happens_before_the_key_grammar_is_applied` still passes —
      pruning makes it more true, not less, since the bad segment is never derived.
- [x] 2.6 (added during apply) Add a test that the skipped set is ordered deterministically,
      pinning task 1.6.

## 3. Read the facet in the listing operation

- [x] 3.1 In `src/spoc/diagnostics/core.py::list_records`, choose the reader by whether
      `kind` was given (`by_kind` versus `all`), keep the `UnknownKindError` check ahead of
      the read, filter on `namespace` only, and drop the outer `sorted` (design D5).
- [x] 3.2 Extend the docstring to say that order comes from the registry read rather than
      being re-established here, and why narrowing costs the facet.

## 4. Pin the listing guarantees

- [x] 4.1 Add a test in `tests/test_diagnostics.py` asserting a kind-narrowed listing
      returns records in canonical identifier order across a registry holding several kinds.
      Added `_multi_kind_project` (two kinds × two apps) plus a composed kind+namespace test,
      since the previous fixture declared only one kind and could not tell a facet read from
      a filtered whole-store read.
- [x] 4.2 Confirm the existing unknown-kind test still fails with `UnknownKindError` naming
      the declared kinds, rather than returning empty.
- [x] 4.3 Add or confirm a test that a namespace narrowing matching nothing returns empty
      rather than raising.

## 5. Validate and close out

- [ ] 5.1 Run `task check` and confirm every gate row passes; report any row that could not
      run as unverified (Rule 6).
- [ ] 5.2 Review the diff and split the commits by intent — the collection traversal and the
      listing read are two changes, not one (Rule 3).
- [ ] 5.3 Run `/opsx:sync` to fold both delta specs into the main specs, then archive with
      `openspec archive -y --skip-specs`.
