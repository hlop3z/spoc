## Why

The kernel's contracts are stated precisely and kept faithfully — until something raises.
A hardening read of `core/` and `framework.py` found seven places where a guarantee holds
only on the happy path, one of them a defect that wedges the framework permanently: when a
module's `teardown()` raises, `shutdown()` never resets kernel state, `started` stays true,
`start()` is then refused as "already started", and every later `shutdown()` re-raises the
same error forever. The only escape is constructing a new `Framework`.

The specs are why it survived. `App-authored lifecycle failures propagate unwrapped` spells
out, for a failed *start*, that the framework "is returned to its inert state"; its
shutdown-hook scenario says only that the error propagates, and stops. `Restart rebuilds
kernel state` says reset happens "after shutdown" without saying whether a shutdown that
failed counts. The code matches the specs exactly; the specs are asymmetric.

Now is the moment because 1.0 makes these contracts binding. Fixing an asymmetry in the
lifecycle guarantee is a patch today and a breaking change afterwards.

## What Changes

- **Shutdown resets kernel state even when teardown fails.** A failing `teardown()` or
  shutdown hook still propagates unwrapped, but the framework reaches its inert state
  first, so it is restartable rather than wedged. Same for the asynchronous path.
- **Start's rollback becomes unconditional.** Rollback currently guards only against
  `Exception`, so a `BaseException` raised *during rollback* skips the reset and leaves a
  populated registry and loader behind for the next `start()` to run discovery over.
- **A resolution failure is composed from one observation of the registry.** The failure
  path currently takes three independent lock acquisitions, so under concurrent
  registration it can name candidates that did not exist at lookup time, or call a
  namespace unknown moments after it was added. The fix acquires the lock *less*, not more.
- **The synchronous path refuses coroutine lifecycle code before invoking any of it.**
  Today the refusal fires when the walk reaches the offending module, so a coroutine
  `initialize()` in the last app boots every earlier app first and then raises.
- **The concurrency suite actually exercises concurrency.**
  `test_racing_duplicates_have_one_winner` calls `.result()` on each submission before
  submitting the next, so its two "racing" threads never overlap — twenty repetitions of a
  sequential case already covered elsewhere. It verifies a spec scenario that therefore has
  no real coverage.
- **The four lifecycle walks stop being four.** Sync and async × initialize and shutdown
  differ only by `await` and the coroutine refusal, and have already drifted: both
  initialize paths log per module, neither shutdown path logs at all.
- **`LoadedModule.initialized` says what it means.** It is set true for modules that have
  no `initialize()` at all, while its comment claims it records that "the module's own
  `initialize()` completed".

No new capability, no new surface, no new dependency. Every item is a promise the kernel
already makes, kept when it currently is not.

## Capabilities

### New Capabilities

None. This change adds no capability; it closes gaps in two that exist.

### Modified Capabilities

- `framework-lifecycle`: the shutdown guarantee becomes symmetric with the start guarantee
  — reaching the inert state is owed whether or not teardown succeeded, and rollback owes it
  whether or not rollback itself succeeded. The synchronous path's coroutine refusal becomes
  a precondition checked before any lifecycle code runs, rather than a failure discovered
  partway through the walk.
- `component-registry`: the concurrency requirement extends from records to *messages* — a
  resolution failure must describe one consistent observation of the registry, not several
  stitched together.

### Concerns for `/ai:decide`

Two items are reliability-sensitive enough that the build-vs-adopt call should be recorded
rather than assumed:

- **Lifecycle state transitions.** `started` is a boolean guarded by a lock and a thread-owner
  field, and this change adds failure edges to that machine. Whether an explicit state
  machine (adopted) beats hand-rolled flags for a three-state lifecycle is the decision;
  the answer may well be "hand-rolled, and here is why", but it should be on the record now
  that failure transitions are being added.
- **Verifying concurrency in tests.** Finding 4 shows the hand-rolled `ThreadPoolExecutor`
  pattern can silently stop testing what it claims. Whether to reach for a race-exercising
  primitive or tool, or to keep the pattern with a barrier, is a real choice — and the suite
  already adopts Hypothesis for the generated-sequence scenario, so the precedent exists.

## Impact

- `src/spoc/framework.py` — `shutdown`, `ashutdown`, `start`, `astart` rollback and reset
  ordering.
- `src/spoc/core/loader.py` — the four lifecycle walks, the coroutine pre-flight check, and
  the `LoadedModule.initialized` field's meaning.
- `src/spoc/core/registry.py` — `resolve`'s failure path only; the success path is
  unchanged and stays a single dict hit.
- `tests/test_concurrency.py`, `tests/test_framework.py`, `tests/test_loader.py` — the
  non-racing test is repaired, and the wedge, the rollback-during-rollback path, and the
  pre-flight refusal each gain coverage they do not currently have.
- `openspec/specs/framework-lifecycle/spec.md` and
  `openspec/specs/component-registry/spec.md` — delta specs, folded on sync.
- Documentation: `docs/architecture/kernel.md` states the lifecycle and concurrency
  invariants and must move with them (Rule 8).
- No public surface changes, so no `apidiff` movement is expected beyond none. No
  dependency changes; `dependencies = []` holds.
- Behaviour visible to an app author changes in one direction only: cases that previously
  wedged or half-booted now fail cleanly. Nothing that worked stops working.
