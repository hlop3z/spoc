## 1. Declare the platform set

- [x] 1.1 Replace `Operating System :: OS Independent` in `pyproject.toml` with the three
      classifiers for Linux, Windows, and macOS
- [x] 1.2 State the platform scope in `.canon/checks.md` — which platforms the gate runs on,
      and why the `go`, `docs-build`, and `doc-links` rows stay single-platform (D4)
- [x] 1.3 Add the operating-system dimension to the `python` job in
      `.github/workflows/ci.yml`: full product of three OSes and three Python versions, no
      exclusions, `fail-fast: false` retained
- [x] 1.4 Check `Taskfile.yml` against the scope statement and reconcile if it disagrees —
      `test:cov` already existed, so the new Coverage row names it rather than inventing one
- [x] 1.5 Find every documented platform claim and align it with the declaration (Rule 8) —
      `CONTRIBUTING.md` claimed twice that a green local suite means a green pipeline, which
      the platform scope makes false; corrected

## 2. Make platform selection a value (D1)

- [x] 2.1 Split `cache.default_cache_root()` into a pure function over an explicit platform
      identifier and environment mapping, plus a thin adapter reading `sys.platform` and
      `os.environ`
- [x] 2.2 Parametrized test covering all four arms — override, Windows, darwin, POSIX — passing
      from any host
- [x] 2.3 Test that a stated override wins on every platform, not only where it is native
- [x] 2.4 Test that the derived location is namespaced to the project
- [x] 2.5 Confirm no arm of `default_cache_root` is host-dependent in coverage: the same lines
      report covered regardless of the platform running the suite

## 3. Correct the revision-to-location mapping (D2)

- [x] 3.1 Replace the lossy filter in `cache.DirectoryCache._entry` with the total mapping:
      verbatim when already a safe path segment, otherwise `rev-<sha256 truncated>`
- [x] 3.2 Refuse an empty revision, naming the reference
- [x] 3.3 State injectivity as a Hypothesis property in `tests/test_properties.py` — distinct
      revisions never resolve to the same retained location (D6)
- [x] 3.3a Keep the collisions actually found as named regression anchors: `feature/x` versus
      `featurex`, `a/b/c` versus `abc`, and two distinct revisions that both filter to empty
- [x] 3.4 Test that a traversal-shaped revision reads and writes nothing outside the
      retention root
- [x] 3.5 Test that a revision already path-safe keeps its verbatim key, so nothing currently
      retained is invalidated
- [x] 3.6 Confirm `HttpRevisionResolver`'s `url-<digest>` keys still round-trip unchanged
      through the new mapping

## 4. Verify retention under concurrency (D3)

- [x] 4.1 Test that a publish failing while the entry exists yields the published entry and
      raises nothing
- [x] 4.2 Test that a publish failing while the entry does not exist raises rather than
      reporting the revision retained
- [x] 4.3 Test that the losing operation leaves no staged directory in the retention root
- [x] 4.4 Test that `retain` on an already-retained revision returns without repopulating

## 5. Exercise the documented retrieval invariants

- [x] 5.1 Test that a transfer exceeding `MAX_TRANSFER_BYTES` is refused naming the bound, and
      that a transfer exactly at the bound is accepted
- [x] 5.2 Test that an insecure redirect encountered during a retrieval propagates as itself
      and is not flattened into a generic retrieval failure
- [x] 5.3 Test that a `gh:` reference naming other than exactly `owner/repo` is refused,
      naming the reference as supplied
- [x] 5.4 Test `HttpRevisionResolver.resolve` in each form: a `gh:` reference resolving to the
      reported commit; a response carrying no usable revision being refused; a pinned reference
      returning its own revision without a request; a direct archive URL yielding a stable
      `url-` digest key
- [x] 5.5 Test that resolving the same direct archive URL twice yields the same key, and two
      different URLs yield different keys
- [x] 5.6 Test `HttpFetcher._url_for` for each scheme: `gh:`, `git+` with and without a `.git`
      suffix, and a direct archive URL used as supplied
- [x] 5.7 Confirm no test in the suite opens a socket

## 6. Reorganize and close out

- [x] 6.1 Move retention tests to `tests/test_scaffold_cache.py`, carrying the socket-free
      declaration into its docstring (D7)
- [x] 6.1a Add the coverage review-aid row to `.canon/checks.md`, marked not-a-gate with the
      reason recorded (D5)
- [x] 6.2 Re-measure coverage for `remote.py` and `cache.py`; for every line still uncovered,
      state why it is unreachable or cover it
- [ ] 6.3 Record the correction in `CHANGELOG.md` under `[Unreleased]` — the aliasing fix under
      `Fixed`, the narrowed platform classifiers under `Changed`
- [ ] 6.4 Update the architecture diagram if the cache-root split changed the shape (Rule 1)
- [ ] 6.5 Run the full gate from `.canon/checks.md` and report any row that could not be run
      as unverified (Rule 6)
- [ ] 6.6 Review the diff and split it into commits by intent (Rule 3)
