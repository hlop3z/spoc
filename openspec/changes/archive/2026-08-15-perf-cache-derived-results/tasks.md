# Tasks — cache derived results computed from immutable inputs

## 1. Registry ordered-view cache (design D1)

- [x] 1.1 Add the facet-keyed ordered-view cache to `Registry.__init__` and clear it
      unconditionally in `_admit`, alongside a docstring line extending the only-mutator
      invariant to the cache.
- [x] 1.2 Route `all()`, `by_kind()`, and `by_namespace()` through the cache: populate the
      sorted result under the existing lock on first read, return `list(cached)` on every
      read. `__iter__` needs no change (it delegates to `all()`).
- [x] 1.3 Tests for the delta scenarios: repeated enumeration does not re-derive order
      (assert via sort-count instrumentation, e.g. a key-function spy), and a registration
      between reads appears in its deterministic position on the next read.
      Also: `TestOneWriter`'s guard became per-attribute rather than a shared writer list,
      so authoritative state stays pinned to `_admit` while the derived cache declares
      `_ordered` with its own atomicity argument.

## 2. Codec failure caching (design D2)

- [x] 2.1 Add the failure map to `FormatRegistry.__init__`; on an `ImportError` from a
      factory, record `(name, direction)` → the context and extra, then raise. On a hit in
      `function`, construct and raise a fresh `MissingDependencyError` without re-running
      the factory. Leave `UnsupportedDirectionError` uncached. Comment the mid-process
      installation trade at the cache-write site.
- [x] 2.2 Tests for the delta scenarios: a second request for an unavailable format does not
      re-invoke the factory (spy on the factory callable), repeated `supported()` calls
      report identical outcomes with one discovery per format/direction, and the raised
      message still names the extra actionably.

## 3. Stub extraction dedup (design D3) — withdrawn

- [x] 3.1 ~~Add the `id(obj)`-keyed local memo around `reference_for`.~~ **Withdrawn.**
      Implemented, then reverted: the registry refuses a second identifier for any tracked
      object (`IdentityDivergenceError`), which is every object whose extraction is
      expensive. Only shared value types can be registered twice, and they take the cheap
      `value` branch — no signature, no type hints. The memo could never pay. Verified
      against the registry directly; reasoning recorded in `_entries`' docstring and D3.
- [x] 3.2 ~~Test that one object registered under several identifiers is extracted once.~~
      **Withdrawn with 3.1** — the premise is unconstructible: registering one callable
      twice raises rather than producing two entries. No test can assert the saving.

## 4. Validation and close-out

- [x] 4.1 Run the checks in `.canon/checks.md`; report anything unrunnable as unverified.

      Every gate row ran on Windows, all green: Formatter (`ruff format --check`, after one
      reformat of `test_registry.py`), Linter (`ruff check`, `go vet ./...`), Type checker
      (`ty check`, `mypy` — 49 files), Stub conformance, Unit tests (**976 passed, 5
      skipped**), Build (`go build`), Doc links, Docs build (`mkdocs --strict`), API surface,
      Tool tests (111 passed), Surface delta.

      Nothing unverified. Three pre-existing, unrelated notes: the 5 skips are docs snippets
      marked `test="skip"` at their source, not host-conditional; API surface reports 2
      `unverifiable` schema kinds; Surface delta reports the 1.0-cut breakages against 0.8.0,
      which it is specified to report without failing before 1.0.

      Review aids not run as gates, per the table: File-size review, Coverage.

- [x] 4.2 Review the diff and commit by intent (Rule 3) — the three sites are three
      separable perf commits unless the diff argues otherwise.

      Reviewing the diff also caught what the design had under-argued: caching *empty*
      facets would let any caller grow the registry's memory with namespace strings that
      match nothing. Only non-empty facets are retained, which bounds the cache by what is
      registered; two tests pin it. Recorded in design.md's risk list.
