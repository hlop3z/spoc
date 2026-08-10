## 1. Establish the baseline

- [x] 1.1 Record the current surface: run `cd scripts/py && uv run apicheck ../..` and
      `uv run apidiff ../..`, and keep both outputs in the session scratchpad as the
      before-state every later comparison is made against.
- [x] 1.2 Confirm the counts the design rests on — 49 names in `spoc.scaffold.__all__`,
      27 carrying the provisional notice — and reconcile any discrepancy before editing.
- [x] 1.3 Confirm no published namespace other than `spoc.scaffold` re-exports these names
      (`spoc/__init__.py` currently does not), so the withdrawal has one place to happen.

## 2. Narrow the published namespace

- [x] 2.1 Remove from `spoc/scaffold/__init__.py` the five port and vocabulary names that
      appear in no public operation's signature: `Reference`, `ReferenceKind`,
      `RevisionResolver`, `Fetcher`, `Cache`.
- [x] 2.2 Remove the retrieval adapters and their values: `HttpRevisionResolver`,
      `HttpFetcher`, `DirectoryCache`, `default_cache_root`, `RemoteTemplateSource`.
- [x] 2.3 Remove the archive-admission values `MAX_EXPANDED_BYTES` and `MAX_MEMBERS`.
      Leave `extract_archive` exported for now — task group 5 owns it, and it stays in
      `__all__` through the deprecation period rather than being withdrawn here.
- [x] 2.4 Remove the record-writing side of provenance: `record_content`, `record_file`,
      `describe_divergence`. Keep `Origin`, `RECORD_NAME`, `read_origin`.
- [x] 2.5 Remove the ten error leaves that admit no distinct response: `PathConflictError`,
      `PathEscapeError`, `IncompleteTemplateSetError`, `UnsatisfiedValueError`,
      `UndeclaredValueError`, `ReservedTargetError`, `InsecureRedirectError`,
      `MemberRefusedError`, `BoundExceededError`, `RevisionUnavailableError`.
- [x] 2.6 Delete the now-unused eager imports at the top of `spoc/scaffold/__init__.py` so
      the import list and `__all__` state the same set, and update the module docstring to
      describe what the package now publishes.
- [x] 2.7 Verify the surviving set is exactly the 19 public and 4 provisional elements the
      design names, plus `extract_archive`, which stays exported and `public` for its
      deprecation period — 24 names in total, down from 49. Confirm
      `python -c "import spoc.scaffold"` still succeeds.

## 3. Settle the notices

- [x] 3.1 Remove the provisional notice from the two elements promoted to `public`:
      `UnrecognizedReferenceError` and `RetrievalError` in `spoc/scaffold/errors.py`.
- [x] 3.2 Remove the now-meaningless provisional notice from every withdrawn element — an
      internal element promises nothing, and a leftover notice claims a tier it no longer
      has. Twenty-one in total, across `plan.py` (5), `errors.py` (5), `provenance.py` (3),
      `archive.py` (3, including `extract_archive`), `remote.py` (2), `cache.py` (2),
      `sources.py` (1).
- [x] 3.3 Extend the notice on `EnumerableSource` in `plan.py` to state its settling
      condition: whether any template source outside this package implements it.
- [x] 3.4 Extend the notices on `Origin`, `RECORD_NAME`, and `read_origin` in
      `provenance.py` to state their shared settling condition: whether the origin record
      must also carry the substitution values a generation used.
- [x] 3.5 Confirm no element outside `spoc.scaffold` gained or lost a notice — the kernel's
      surface is out of scope and must be unchanged.

## 4. Repoint internal importers

- [x] 4.1 Confirm `spoc/cli.py` and `spoc/scaffold/cli.py` still import successfully; both
      already reach submodules directly, so this is a check rather than an edit.
- [x] 4.2 Repoint the scaffold test modules that import withdrawn names from the package
      to their defining submodules: `tests/test_scaffold.py`,
      `tests/test_scaffold_archive.py`, `tests/test_scaffold_parity.py`,
      `tests/test_scaffold_provenance.py`, `tests/test_scaffold_remote.py`.
- [x] 4.3 Run the full test suite and confirm every failure is an import path, not a
      behaviour change. A behavioural failure means the withdrawal touched something it
      should not have.

## 5. Exercise the deprecation lifecycle on `extract_archive`

- [x] 5.1 In `spoc/scaffold/__init__.py`, bind `extract_archive` to the PEP 702 decorator
      from `spoc.core.deprecation` applied to `spoc.scaffold.archive.extract_archive`,
      keeping the name in `__all__` — it stays `public` until removal, which is what a
      lifecycle means. The message names the submodule import as the migration and removal
      at 1.0 as the schedule.
- [x] 5.2 Verify on both 3.12 and 3.13+ that the warning fires through `spoc.scaffold` and
      not through `spoc.scaffold.archive`. The decorator stamps `__deprecated__` on the
      object it is given as well as on the wrapper it returns; if a type checker flags the
      submodule path as a result, bind the decorated wrapper to a private name in
      `archive.py` and re-export that, so the stamp never lands on the function itself.
- [x] 5.3 Add a test asserting both halves of the contract: reaching `extract_archive`
      through `spoc.scaffold` warns, and reaching it through `spoc.scaffold.archive` does
      not. Without the second assertion the migration path is unverified.
- [x] 5.4 Confirm the two names now refer to different objects and that nothing in the
      package or the test suite compares `extract_archive` by identity.
- [x] 5.5 Record what `apicheck` and `apidiff` actually report for the decorated
      re-export — the design predicts a `public` element visible to griffe and marked
      deprecated. Write down the observed behaviour; if it differs, the design is what
      needs correcting, not the observation.

## 6. Enforce the settling condition

- [x] 6.1 Extend `apicheck` so a `provisional` element whose documentation carries only the
      boilerplate notice, with no further prose, is a finding.
- [x] 6.2 State the check's limitation where it is defined: it can detect a bare hedge but
      cannot judge whether a stated settling condition is meaningful.
- [x] 6.3 Add tests for both outcomes — a bare notice is a finding, a notice with a
      settling condition is not — in `scripts/py/tools/apicheck/tests/`.
- [x] 6.4 Run `apicheck` against the working tree and confirm zero fatal findings, with the
      four provisional survivors passing the new rule.

## 7. Documentation

- [x] 7.1 Update the published stability documentation to describe what `spoc.scaffold`
      promises, and to state plainly that a withdrawn element remains importable from its
      submodule while promising nothing.
- [x] 7.2 Correct any documentation page or example that imports a withdrawn name from
      `spoc.scaffold`, and execute every snippet touched rather than reading it.
- [x] 7.3 Update the architecture diagram in `docs/architecture/` if the published-surface
      boundary it draws no longer matches (Rule 1).
- [x] 7.4 Record the surface changes in `CHANGELOG.md`: each of the 25 withdrawals named
      individually, the 2 promotions, the 4 provisional survivors with their settling
      conditions, and the `extract_archive` deprecation with its removal schedule.

## 8. Validate and close

- [x] 8.1 Run every row in `.canon/checks.md` and record the result of each, naming any
      row that could not be run rather than omitting it (Rule 6).
- [x] 8.2 Compare `apidiff` output against the task 1.1 baseline and confirm every reported
      removal and tier movement is one this change intended — an unexplained entry means
      something was withdrawn by accident.
- [x] 8.3 Confirm `dependencies = []` in `pyproject.toml` is unchanged and no import of a
      third-party package entered `src/spoc/`.
- [x] 8.4 Review the full diff and split it into commits by intent (Rule 3).
