## 1. Pin the defects before changing anything

- [x] 1.1 Add a failing test that a raising `teardown()` leaves the framework restartable:
      after the failure, `started` is false, the registry and config are reset, and a second
      `start()` succeeds
- [x] 1.2 Add a failing test that a second `shutdown()` after a failed one is a harmless
      no-op rather than a re-raise of the same teardown failure
- [x] 1.3 Add a failing test for the same guarantee on the asynchronous path
      (`ashutdown` with a coroutine teardown that raises)
- [x] 1.4 Add a failing test that a failure *during rollback* still leaves the framework
      inert, and that the exception reaching the caller is the one that failed the boot
- [x] 1.5 Add a failing test that the synchronous path refuses a coroutine `initialize()`
      declared by the last module in load order without having run any earlier module's
      `initialize()` or any startup hook
- [x] 1.6 Confirm 1.1–1.5 all fail against current `main` for the stated reason, not an
      incidental one — a test that passes here is testing the wrong thing

## 2. Make reaching the inert state unconditional

- [x] 2.1 Add the private helper that performs a transition's teardown attempt and
      guarantees `_reset()` and `_started = False` in a `finally` (design Decision 1)
- [x] 2.2 Route `shutdown()` and `ashutdown()` through it, leaving each path's own locking
      untouched — the blocking context manager for sync, the non-blocking acquire for async
- [x] 2.3 Route `start()`'s and `astart()`'s rollback through it so `_reset()` cannot be
      skipped by a `BaseException` raised during rollback
- [x] 2.4 Catch the cleanup failure including `BaseException`, log it at error level with
      `exc_info=True` on the module's own `__name__` logger, and re-raise the original bare so
      the app-authored type and traceback reach the caller unchanged (Decision 2, and the
      logging ADR — lazy `%s` args, never pre-formatted text)
- [x] 2.5 Verify 1.1–1.4 now pass, and that `test_shutdown_hook_error_propagates_unwrapped`
      and `test_shutdown_hook_fires_when_module_initialize_raises` still pass unchanged

Tasks 2.6–2.9 are prerequisites of 2.4: without them the new error-level log ships as stderr
noise. Recorded in the logging build-vs-adopt ADR.

- [x] 2.6 Register a `NullHandler` on the `spoc` root logger at the package root, so
      `lastResort` cannot print the new error record in an application that never configured
      logging
- [x] 2.7 Replace `core/loader.py`'s hardcoded `getLogger("spoc")` with `getLogger(__name__)`,
      matching `core/config.py` — one convention, and per-subsystem levels for consumers
- [x] 2.8 Add a test that importing `spoc` and triggering the cleanup-failure path emits
      nothing to stderr under a default (unconfigured) logging setup, and that the record is
      still there for a consumer who attaches a handler
- [x] 2.9 State the logger-name contract where a consumer configuring logging would look:
      `spoc` is the stable handle, names below it follow module paths and are internal

## 3. Compose a resolution failure from one observation

- [x] 3.1 Take the lookup and — only on a miss — one snapshot of the store in the same lock
      acquisition in `Registry.resolve` (Decision 4)
- [x] 3.2 Derive the kind, namespace, and candidate-name checks from that snapshot in pure
      code, with no further locking; delete the `namespaces()` / `by_kind()` calls from the
      failure path
- [x] 3.3 Confirm the success path is unchanged: one acquisition, one dict hit, no snapshot
      allocated
- [x] 3.4 Assert the per-segment failure messages are byte-identical to before for every
      existing case in `tests/test_registry.py` — this is a locking change, not a message
      change
- [x] 3.5 Correct the `Registry` class docstring, which currently claims single-lock reads
      that the failure path did not deliver

## 4. Make the concurrency suite exercise concurrency

- [x] 4.1 Repair `test_racing_duplicates_have_one_winner`: submit both attempts before
      collecting either, matching `test_racing_starts_have_one_winner`
- [x] 4.2 Release both threads from a `threading.Barrier` so the overlap is established rather
      than assumed (build-vs-adopt ADR: Extend with the stdlib primitive)
- [x] 4.3 Add coverage that a resolution failure never names a candidate absent from the
      observation that failed, under concurrent registration. If a barrier cannot make this
      reliable, adopt `blanket` for this test rather than tolerating flakiness or dropping the
      coverage (the ADR's recorded revisit trigger) — do not settle for a probabilistic pass
- [x] 4.4 Audit the remaining tests in `tests/test_concurrency.py` for the same
      submit-then-block shape and repair any others found

## 5. Collapse the four lifecycle walks into two drivers

- [x] 5.1 Add a test asserting the synchronous and asynchronous paths are behaviourally
      paired — same order, same hook dispatch, same `started`/`initialized` bookkeeping —
      so the refactor is verified against behaviour (Decision 6 mitigation)
- [x] 5.2 Extract one private generator per phase yielding the ordered steps and owning the
      flag bookkeeping
- [x] 5.3 Reduce `initialize`/`ainitialize` and `shutdown`/`ashutdown` to drivers that only
      call or await
- [x] 5.4 Resolve the logging asymmetry the duplication produced — both shutdown paths log
      per module as both initialize paths already do
- [x] 5.5 Correct the `LoadedModule.initialized` field comment: the flag records that the
      module went through the initialize phase, whether or not it defined an `initialize()`,
      and that its `teardown()` is therefore owed (Decision 7)
- [x] 5.6 Stop and report rather than defend the diff if the result reads worse than the
      four loops it replaced

## 6. Refuse coroutines before running any lifecycle code

- [x] 6.1 Add the pre-flight scan to `initialize`, covering startup hooks and module
      `initialize` functions, raising before the first invocation (Decision 8)
- [x] 6.2 Add the same scan to `shutdown` for shutdown hooks and `teardown` functions
- [x] 6.3 Have the refusal name every offender found rather than only the first
- [x] 6.4 Verify 1.5 passes and that the existing coroutine-refusal tests still pass with
      their error text intact where they assert on it

## 7. Move the documentation with the code

- [x] 7.1 Update `docs/architecture/kernel.md` — the lifecycle and concurrency invariants
      state the guarantees this change makes unconditional (Rule 8)
- [x] 7.2 Check the lifecycle and registry API pages for any statement about shutdown,
      rollback, or resolution failure that this change makes stale
- [x] 7.3 Record the accepted leak from Decision 5 where an app author would look for it,
      not only in the change artifacts

## 8. Validate

- [x] 8.1 Run the full `.canon/checks.md` gate via `task check` and report any row that
      does not pass
- [x] 8.2 Confirm `apidiff` shows no new public-surface movement — this change is internal
- [x] 8.3 Confirm `dependencies = []` still holds and the core still imports nothing outside
      the kernel
- [x] 8.4 Re-run the tests from section 1 against the finished change and confirm each fails
      for no reason at all now
