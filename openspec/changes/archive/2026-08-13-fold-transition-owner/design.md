## Context

`Framework` carries two pieces of state describing the same window, written together in
`_begin_transition` and cleared together in `_end_transition`:

- `_transition_owner` — the thread ident that opened the transition. Read by exactly one
  caller, `_refuse_reentry`.
- `_active_transitions` — a `ContextVar[frozenset[Framework]]` holding the frameworks whose
  transition the current thread *or task* is inside. Read by `_inside_transition`, which
  `_refuse_racing_read` uses to decide whether a read is refused.

Both answer "is this caller part of the transition?" — one for a further transition, one for
a read. `_active_transitions` was added by `close-shutdown-read-race` (archived
2026-08-13) specifically because thread identity cannot answer that question on the
asynchronous path. `_transition_owner` predates it and was left alone, with the question
recorded as open in that change's `design.md`. This change closes it.

The defect is not hypothetical. `astart` and `ashutdown` call `_refuse_reentry` *before*
attempting the lock (`framework.py:429`, `:473`), and the sync `_transition` context manager
does the same before acquiring it (`:390`). So on the asynchronous path, an unrelated task
that merely shares the event loop thread matches `_transition_owner` and is told it was
"called from inside a lifecycle transition already running on this thread" — when it is a
racing caller whose correct remedy is to retry after the transition settles. The very next
statement holds the honest error it should have received.

The two existing reentrancy tests (`tests/test_framework.py:1127`, `:1142`) are synchronous
inline calls and pass under either mechanism. Nothing tests the asynchronous cases, which is
why the current check "passes by accident" there.

## Goals / Non-Goals

**Goals:**

- One determination of transition membership, applied to both reads and further
  transitions.
- A racing asynchronous caller receives the concurrent-transition error, not the reentrancy
  error.
- `_transition_owner` is gone, not merely unused.
- The asynchronous cases that change behaviour gain tests; the synchronous ones keep theirs.

**Non-Goals:**

- Draining, blocking, or otherwise coordinating in-flight readers. Settled by the archived
  change: the drain belongs to the transport, and SPOC refuses rather than waits.
- Making a hook that spawns a *thread* and joins it work. It deadlocks on the synchronous
  lock today and still will; see Risks.
- Any change to the lock, to serialization, or to which transitions are permitted to nest
  (nesting stays per framework — one framework's hook may still start another).
- Any public API change. `_transition_owner` is a private attribute.

## Decisions

### D1 — Decide reentrancy with the existing context marker, not thread identity

`_refuse_reentry` becomes a call to `self._inside_transition()`. Membership is then read
from `_active_transitions` for every purpose.

*Why this over the alternatives:*

- **Keep thread identity as well, and refuse if either matches.** Rejected: it preserves the
  misdiagnosis exactly, because the thread-ident arm is what fires first for a racing async
  task. Two mechanisms where one suffices is also the drift risk the archived change removed
  when it collapsed the sync/async discriminators into one.
- **Pair thread identity with the current task identity.** Rejected: this rebuilds, by hand,
  the propagation rule `contextvars` already implements — and would still get spawned work
  wrong, since a task the hook created has its own identity but genuinely is inside the
  transition.
- **Ask the lock who owns it.** Rejected: `threading.Lock` exposes no owner, and switching to
  `RLock` to obtain one would make reentrancy *succeed* — the deadlock-to-error fix that
  landed earlier, undone.

The build-vs-adopt call is inherited, not new: `close-shutdown-read-race` recorded "adopt
stdlib `contextvars`" for transition membership. This change widens the adopted mechanism's
use rather than introducing a competing one, which is the outcome that ADR argued for.

### D2 — The membership check stays ahead of the lock

Order is load-bearing and unchanged: membership first, lock second. Inside-the-transition
callers must be rejected before touching a non-reentrant lock they would deadlock on;
everyone else falls through to the lock, which blocks on the synchronous path and fails fast
on the asynchronous one. Reversing the order would restore the original deadlock.

### D3 — Delete the attribute rather than keep it for diagnostics

`_transition_owner` could be retained purely to report which thread opened a transition.
Rejected: nobody consumes it, it would need clearing in `_end_transition` forever, and a
field kept "for diagnostics" is how the second mechanism grew in the first place. The
project takes withdrawals outright rather than shimmed.

### D4 — The reentrancy message stops naming the thread

"already running on this thread" was a statement about the detector, not the defect. What
makes the inner call wrong is that the transition is mid-flight and its state half-built —
true regardless of where the caller runs. The message keeps naming the offending call
(`start()`, `astart()`, …) so the existing `"inside a lifecycle transition"` assertions in
both tests remain valid.

### Decision: Lifecycle transition membership and reentrancy — Adopt stdlib `contextvars`

- **Status**: approved
- **Why**: The mechanism is already adopted here for read-membership (ADR in
  `2026-08-13-close-shutdown-read-race`); what is new is its *scope* — it now answers
  reentrancy too, and the competing thread-identity mechanism is deleted rather than left
  beside it. `contextvars` is the only option whose isolation rules are correct on both
  lifecycle paths without hand-written propagation, and it costs no dependency.
- **Considered**: OpenTelemetry's `Context` API — mature and standard, but its Python
  implementation is itself a single `ContextVar` (`ContextVarsRuntimeContext`, with
  `threading.local` kept only as a legacy fallback), so it would add a kernel dependency
  for control flow and buy nothing. Retaining thread identity alongside the marker —
  preserves the async misdiagnosis exactly, since the thread-ident arm fires first.
- **Isolation**: `_active_transitions` (module-level `ContextVar`) read through exactly two
  private methods, `_inside_transition` and the `_begin_transition`/`_end_transition` pair.
  No caller outside `Framework` touches it, and no public name exposes it.

## Risks / Trade-offs

- **A hook that spawns an OS thread and joins it still deadlocks on the synchronous path.**
  A new thread starts with an empty context, so it is outside the transition and blocks on
  the held lock — exactly as it does today under the thread-ident check, since its ident
  differs too. → Unchanged behaviour, so out of scope for this change; recorded here so the
  asymmetry is not mistaken for a regression. The `_active_transitions` docstring says work
  a hook spawns inherits the marker; that is true of tasks (context is copied at creation)
  and of `asyncio.to_thread` (which copies the context), and false of a bare
  `threading.Thread`. The comment gets that qualification.
- **Any caller matching on the reentrancy message text breaks.** → Pre-1.0, the error type
  is unchanged, and the message was wrong for the affected case. This is the reason the
  change is sequenced before the 1.0 cut rather than after it.
- **A racing async caller now gets a different error than before.** → That is the point, and
  it is pinned by a new scenario so a later refactor cannot quietly restore the old answer.

## Migration Plan

None required. `_transition_owner` is private and unexported; `apidiff` should report no
change at all for this work. Rollback is reverting the commit — there is no persisted state,
no schema, and no on-disk format involved.

## Open Questions

None. The question this change exists to answer was the last one recorded against
`close-shutdown-read-race`.
