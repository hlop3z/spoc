## Context

`Framework` holds a three-state lifecycle — inert, started, transitioning — in a boolean
(`_started`), a `threading.Lock`, and an owner-thread field. `start()` wraps its work in
`try/except BaseException`, rolls back, calls `_reset()`, and re-raises, so a failed boot is
guaranteed to land inert. `shutdown()` has no equivalent: `loader.shutdown()`, `_reset()`,
and `_started = False` run in sequence at `framework.py:372-374`, so a raising teardown
skips the last two.

That was probed, not inferred. A module whose `teardown()` raises leaves `started` true, the
registry and config populated, `start()` refused as "already started", and every subsequent
`shutdown()` re-raising the same error — because `entry.initialized = False` at
`loader.py:275` is never reached either, so the loader keeps offering the same failing
teardown forever. The framework is unrecoverable without constructing a new one.

The registry has the same shape of gap in miniature. `resolve()` looks up under the lock,
releases, then calls `namespaces()` and `by_kind()` — each re-acquiring — so a failure
message can span three observations while the class docstring claims reads are single-lock.

Constraints that shape the whole design: zero runtime dependencies is an invariant, the core
performs no I/O and imports nothing outside the kernel, app-authored failures must propagate
with their original type and traceback, and the asynchronous path deliberately does *not*
share the synchronous path's blocking lock acquisition because an event loop must never park
on a lock.

## Goals / Non-Goals

**Goals:**

- Reaching the inert state becomes unconditional on every transition out of started, on both
  paths, without weakening unwrapped propagation.
- A resolution failure describes one observation of the registry, using fewer lock
  acquisitions than today rather than more.
- The synchronous path's coroutine refusal becomes a precondition, so it costs no side
  effects.
- The four lifecycle walks stop being four independent copies that can drift.
- Every claim a docstring or field comment makes about failure behaviour matches the code.

**Non-Goals:**

- Changing what a successful boot or shutdown does. The happy path is untouched.
- Recovering resources whose teardown never ran. See Decision 5 — this change chooses
  restartable-with-a-leak over wedged, and does not attempt best-effort continuation.
- Reloading modules on restart. The existing contract that module-level code runs once per
  process stands.
- Any change to the public surface, the CLI, or dependencies.

## Decisions

### Decision 1: One obligation holder, four callers — not a state machine

The reset obligation moves into a single private helper that performs a teardown attempt and
guarantees `_reset()` and `_started = False` in a `finally`, used by all four transition
methods. The methods keep their own locking: the synchronous pair keeps the `_transition()`
context manager, the asynchronous pair keeps its non-blocking acquire, because that
difference is deliberate and load-bearing.

Rejected: modelling the lifecycle as an explicit state machine. It would centralize the
transitions properly, but the machine has three states and this change adds two failure
edges — the abstraction would be larger than what it abstracts, and it is a new dependency
or a new hand-rolled component either way. Recorded as an `/ai:decide` concern rather than
settled here.

Rejected: `try/finally` inline in each of the four methods. It works and is the smallest
diff, but it puts the same four-line obligation in four places — the exact condition that
produced Finding 5.

### Decision 2: The cause wins; the cleanup failure is logged, never silently swallowed

When both the transition's app-authored code and the cleanup that follows fail, the caller
sees the app-authored failure. The cleanup failure is caught — including `BaseException`, so
that reset is genuinely unconditional — and logged at error level on the `spoc` logger
before the original is re-raised bare.

Catching `BaseException` around cleanup is the uncomfortable part, since it includes
`KeyboardInterrupt`. It is acceptable only because the scope is one cleanup call, the
exception is logged rather than discarded, and the process is already unwinding a failure
the caller must handle. What is never suppressed is a `BaseException` that *is* the outcome
— only one raised while cleaning up after a different failure.

Rejected: `ExceptionGroup` carrying both. It is the more complete answer and it breaks
`App-authored lifecycle failures propagate unwrapped`, which promises the caller the exact
type the app raised. Fidelity to the stated contract wins over completeness of reporting.

### Decision 3: The repeat-shutdown no-op falls out of the fix

Once shutdown resets unconditionally, a second `shutdown()` after a failed one finds
`_started` false and a fresh loader, so it takes the existing never-started no-op path. No
separate mechanism is needed, and the spec scenario covering it is a regression test on
Decision 1 rather than on new code.

### Decision 4: `resolve()` takes one lock acquisition, not three

The lookup and — only when it misses — a snapshot of the store are taken in the same `with
self._lock` block. Everything the failure needs (which kinds exist, which namespaces exist
for the parsed kind, which object names exist in that namespace) is then derived from that
snapshot in pure code, with no further locking.

The success path improves: one acquisition, no allocation, still a single dict hit. The
failure path drops from up to four acquisitions to one. This is the rare fix that makes the
contract stronger and the mechanism cheaper, which is why it is worth doing even though the
divergence is benign while registration stays boot-time.

Rejected: holding the lock across message composition. It meets the letter of the guarantee
and holds exclusive access across string formatting, which the spec now explicitly forbids.

### Decision 5: A raising teardown skips the teardowns behind it, and we accept that

After this change a teardown that raises still aborts the walk, so modules earlier in reverse
order never get torn down — and because the loader is then discarded by `_reset()`, they
never will. That is a resource leak, and it is a deliberate trade against the wedge it
replaces: unrecoverable-and-leaking becomes restartable-and-leaking, with the failure loud
either way.

Rejected: continuing the walk best-effort and reporting every failure. It is the better
behaviour on its own terms and it requires either swallowing failures or an
`ExceptionGroup`, which Decision 2 has already ruled out. If unwrapped propagation is ever
revisited, this is the first thing to reconsider — noted in the spec's own terms rather than
left as folklore.

### Decision 6: The walks share their order and bookkeeping, not their invocation

Each phase gets one private generator that yields the steps in order — the entry, the hook
to fire, the module function to call — and owns the flag bookkeeping. The synchronous and
asynchronous drivers consume the same generator and differ only in whether they call or
await. That collapses ordering, hook lookup, and the `started`/`initialized` bookkeeping to
one place per phase while keeping `async def` where it belongs.

Rejected: keeping four walks plus a parity test. Cheaper, and it institutionalizes the
duplication rather than removing it — Rule 7 prefers consolidation over the minimal diff.

Rejected: shared helpers for bookkeeping only. It removes the least interesting duplication
and leaves the ordering logic copied four times, which is where drift actually hurts.

### Decision 7: Fix the comment, keep the field name

`LoadedModule.initialized` is set true for modules with no `initialize()` at all. The
behaviour is right — a module that went through the initialize phase owes its teardown — and
the field name is right for that meaning. Only the comment claiming "the module's own
`initialize()` completed" is wrong, and it is what gets corrected.

Rejected: renaming to something like `teardown_owed`. More precise, and it churns an internal
type `apidiff` is already reporting movement on, for no behavioural gain.

### Decision 8: Each phase's pre-flight covers only that phase

`initialize` establishes that no startup hook and no module `initialize` it is about to run
is a coroutine, before running any of them; `shutdown` does the same for shutdown hooks and
`teardown`. The refusal names every offender found, not just the first.

Rejected: one scan at start covering teardowns too. It would refuse earlier for a coroutine
`teardown`, but it makes a start fail over a shutdown-time concern, and `spoc check` already
reports both up front — that is precisely its job.

## Build-vs-Adopt Decisions

### Decision: Lifecycle state transitions — Build, hand-written flags under one lock

- **Status**: approved
- **Why**: `dependencies = []` is an enforced invariant, so any runtime library is
  architecturally incompatible — the hierarchy's own stated ground for Build. The machine has
  three states and this change adds two failure edges; an adopted framework would be larger
  than the thing it models, and Decision 1 already consolidates the obligation to one holder,
  which is the actual defect being fixed.
- **Considered**: `python-statemachine` 2.6.0 (released 1 Aug 2026, Production/Stable, guards
  and validators, full async support — the best fit on merit, and it would be the kernel's
  first runtime dependency); `transitions` (long-standing, lightweight, extensible; same fatal
  objection).
- **Revisit trigger**: if the lifecycle ever grows states beyond inert/started/transitioning
  or gains conditional transitions, re-run this decision — the objection is the dependency
  invariant plus current size, not the libraries' quality.
- **Isolation**: the private transition helper from Decision 1, the single place the flags and
  the lock are touched.

### Decision: Verifying concurrency in tests — Extend the existing pattern with `threading.Barrier`

- **Status**: approved
- **Why**: test-only, so the runtime dependency invariant does not bind — and the stdlib
  primitive is what the official Python free-threading guide recommends for exactly this
  purpose: place a barrier before the line suspected of racing so workers are released
  together. It converts task 4.2 from "assume the threads overlapped" to "establish that they
  did", which is the whole content of Finding 4.
- **Considered**: `blanket` (deterministic concurrency testing — wraps threading primitives
  and drives execution from the main thread, so a test chooses which thread takes the lock
  next; genuinely better for task 4.3's otherwise-probabilistic resolve race, but it
  intercepts threading primitives and is new); `pytest-run-parallel` (Quansight-Labs; runs one
  test in many threads, strong for broad thread-safety sweeps, unable to express "these two
  operations must overlap").
- **Revisit trigger**: if task 4.3 cannot be made reliable with a barrier, adopt `blanket` for
  that test rather than accepting a flaky one or deleting the coverage.
- **Isolation**: the concurrency test module. No barrier appears in `src/`.

### Decision: The failure-path log — Adopt the standard library's `logging`, bridgeable but unbridged

- **Status**: approved
- **Why**: stdlib `logging` is the mature standard for a library's position in the stack, and
  the 2026 guidance is explicit that a library emits to a named logger while the *application*
  owns the telemetry pipeline. Three consequences are taken deliberately rather than left
  incidental:
  - **A `NullHandler` on the `spoc` root logger.** Without one, Python's `lastResort` handler
    prints WARNING and above to stderr, so the error-level cleanup log this change introduces
    would appear unbidden in every application that never configured logging. Adding the log
    without the handler would be shipping noise.
  - **Hierarchical names via `getLogger(__name__)` everywhere.** `core/loader.py:36` hardcodes
    `getLogger("spoc")` while `core/config.py:34` uses `__name__`; two conventions in one core.
    Unifying gives a consumer per-subsystem control (raise the loader's level, leave the rest)
    and removes a hardcoded string that drifts when modules move.
  - **Lazy `%s` arguments and `exc_info=True`, never pre-formatted text.** This is what keeps
    the choice OTel-*bridgeable without an OTel dependency*: an application routing stdlib
    records into OpenTelemetry's `LoggingHandler` receives the cleanup failure as a structured
    exception record with attributes, not a string blob it has to parse back apart.
- **The logger-name contract, stated so it can be relied on**: `spoc` is the stable handle a
  consumer configures. Names below it follow module paths and are internal, so relocating a
  module is not a silent breaking change for someone's logging config. Recording this now is
  what stops logger names from becoming an accidental part of the public surface.
- **Considered**: bridging to OpenTelemetry directly (the literal reading of the never-hand-roll
  list; needs an intercept layer and OTel packages — a runtime dependency for a concern the
  consuming application owns, and the canon's rule addresses applications, not libraries);
  `structlog` (better structured-logging DX, still a runtime dependency); leaving the naming
  inconsistency alone (minimal diff, keeps two conventions and ships the stderr noise).
- **Isolation**: one `NullHandler` registration at the package root; every module keeps its own
  `__name__` logger and nothing else touches logging configuration.

## Risks / Trade-offs

- **Catching `BaseException` around cleanup could mask a `KeyboardInterrupt`** → scoped to
  one call, logged at error level rather than discarded, and never applied to an exception
  that is itself the outcome (Decision 2).
- **The generator refactor could read worse than the four loops it replaces** → the parity
  and wedge tests land *before* the refactor, so it is verified against behaviour rather
  than reviewed by eye. If the result is less legible than what it replaced, that is a
  finding to raise, not a diff to defend.
- **The pre-flight scan changes when the refusal surfaces** → a project that currently boots
  several apps before being refused will now be refused first. Only side effects that were
  never promised disappear; pre-1.0 allows the change, and the error gains information
  (every offender, not the first).
- **Skipped teardowns leak** → accepted and stated in Decision 5, with the failure still
  loud. The alternative was ruled out by a contract this change is not reopening.
- **Tests for concurrent failure paths are inherently probabilistic** → the racing-duplicate
  repair (Finding 4) is what makes the difference detectable at all; a barrier or an adopted
  race primitive is an `/ai:decide` concern below, not an assumption here.

## Migration Plan

No migration. No public element changes, no configuration changes, no data formats. The
observable difference is confined to cases that previously wedged or half-booted, which now
fail cleanly — nothing that worked stops working, so the change ships in a normal minor
release with the pre-1.0 allowance unused.

Rollback is `git revert`: the change adds no state, no file, and no schema.

## Open Questions

Both are deferred to `/ai:decide` and named in the proposal:

1. **Lifecycle state transitions** — hand-rolled flags plus a lock, or an adopted state
   machine? Decision 1 proceeds with hand-rolled and explains why the abstraction would
   exceed what it abstracts, but this change adds failure edges to that machine and the call
   should be on the record rather than assumed.
2. **Verifying concurrency in tests** — keep the `ThreadPoolExecutor` pattern with an
   explicit barrier, or adopt a race-exercising tool? Finding 4 is direct evidence the
   current pattern can stop testing what it claims without anyone noticing, and Hypothesis
   is already adopted for the generated-sequence scenario, so a precedent for adopting
   exists.
