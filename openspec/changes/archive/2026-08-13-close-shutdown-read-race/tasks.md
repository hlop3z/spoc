## 1. Decision gate

- [x] 1.1 Run `/ai:decide` for the **reader draining** concern — approved: Adopt the host's
      drain; `readerwriterlock`/`aiorwlock` and an epoch counter both declined
- [x] 1.2 Run `/ai:decide` for the **transition membership** concern — approved: Adopt
      stdlib `contextvars`, one mechanism for both lifecycle paths
- [x] 1.3 Settled: the refusal covers **all transitions** — start's incremental discovery
      and a failed boot's rollback have the same two windows; everyone legitimate during a
      boot is inside the transition and exempt (ADR in design.md)

## 2. The error

- [x] 2.1 Add the transitioning error to `src/spoc/core/exceptions.py` as a `SpocError`
      subclass, carrying the requested identifier as an attribute and naming the remedy
      (order the call) rather than a segment
- [x] 2.2 Export it from `src/spoc/__init__.py` with a tier stated where it is defined
- [x] 2.3 `apicheck` passes: 0 fatal findings, and `apidiff` reports
      `added: spoc.FrameworkTransitioningError (public)` alongside the rest of the family

## 3. Transition membership

- [x] 3.1 Add a module-level `ContextVar` marking an in-flight transition, set and reset by
      token in `_transition`'s existing `finally`
- [x] 3.2 Set and reset the same marker on the asynchronous paths, which manage the lock
      by hand rather than through `_transition` (`astart`, `ashutdown`)
- [x] 3.3 Expose one private membership predicate that both lifecycle paths and the read
      path consume, so "inside the transition" is described once
- [x] 3.4 Leave `_transition_owner` in place — it answers reentrancy, a different question
      from membership; note whether it could later be folded into the marker

## 4. The refusal

- [x] 4.1 Refuse reads from outside an in-flight transition in `Framework.resolve`
- [x] 4.2 Apply the same refusal to `resolve_type` and `resolve_object`
- [x] 4.3 Verify `_components_for` still reads the registry it bound at phase start and is
      unaffected by the refusal

## 5. Tests

- [x] 5.1 Window A: a read during teardown raises the transitioning error
- [x] 5.2 Window B: a read after the registry reset raises the transitioning error, not an
      unknown-segment error
- [x] 5.3 A genuine typo still raises the unknown-namespace error with its candidates
- [x] 5.4 A settled framework resolves with no added failure mode
- [x] 5.5 Teardown exemption: a module `teardown()` resolves successfully mid-shutdown
- [x] 5.6 The exemption does not leak: a teardown read succeeds while a concurrent
      unrelated read is refused
- [x] 5.7 The exemption ends with the transition
- [x] 5.8 Both lifecycle paths classify inside/outside identically, covering all four
      verified cases: racing thread, racing task predating the transition, teardown hook
      awaited inline, and work spawned by teardown
- [x] 5.9 The marker is reset after a transition — a read following a completed shutdown
      is not exempt on the thread or task that ran it
- [x] 5.10 Shutdown does not block on a repeatedly-resolving reader
- [x] 5.11 The starter template still starts and shuts down end to end — covered by the
      existing `test_scaffold_starter.py` tests; its `_close` hook takes the components it
      is passed, so it never depended on the exemption
- [x] 5.12 `resolve_type` and `resolve_object` refuse on the same terms as `resolve`
- [x] 5.13 Start refuses an outside read mid-boot with the transitioning error, and in-boot
      code (module import, ready callback, startup hook, `initialize()`) still resolves
- [x] 5.14 A read racing a failed boot's rollback gets the transitioning error, not an
      unknown-segment error
- [x] 5.15 A never-started framework still answers unknown-segment against its empty
      registry — the refusal covers transitions, not the inert state

## 6. Documentation

- [x] 6.1 Rewrite `Framework`'s concurrency docstring: the transitioning refusal, the
      teardown exemption, and that the drain is the host's
- [x] 6.2 Restate invariant 9 in `docs/architecture/kernel.md` — drop the atomic-swap
      guarantee, state draining ownership
- [x] 6.3 Add per-surface shutdown guidance to `docs/docs/how-to/ship-a-framework.md`:
      call it from the lifespan shutdown handler, or after the RPC server's graceful stop
      returns, and name the cases with no ambient drain (message-queue loops, app-spawned
      background tasks, worker threads, CLIs)
- [x] 6.4 Added the new error to `docs/docs/api/errors.md` (the docs-integrity gate
      requires a row per exported exception) and the use-past-a-transition exclusion to
      `docs/docs/api/stability.md`. No tier entry is needed: `derive_tier` assigns
      `public` to anything exposed from the package without a provisional notice
- [x] 6.5 Confirm every documentation example still runs under `tests/test_docs_examples.py`

## 7. Validation

- [x] 7.1 Run `task check` and read the exit code directly
- [x] 7.2 Confirm `apidiff` reports the added public name and no `violated:` line
- [x] 7.3 Synced both deltas into the main specs (28 validate, up from 28 with two
      modified and three added requirements), then archived with `--skip-specs`
