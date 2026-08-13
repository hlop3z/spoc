## Context

`Framework.shutdown` runs two steps under the transition lock: `loader.shutdown(...)`, then
`_reset()`. A concurrent `resolve` is answered differently depending on which step it lands in.

```
   shutdown()  ── holds _transition_lock ───────────────────────────────┐
                                                                        │
   ┌─ Window A ─ loader.shutdown(hooks, components_for)                 │
   │             on_shutdown hooks, module teardown()                   │
   │   a concurrent resolve() SUCCEEDS and returns a component whose    │
   │   teardown has already run. No error, no signal.                   │
   │                                                                     │
   ├─ Window B ─ _reset(): registry = Registry(kinds)                   │
   │   a concurrent resolve() hits the old registry (succeeds) or the   │
   │   new one (UnknownNamespaceError — indistinguishable from a typo)  │
   │                                                                     │
   └─ _started = False ─────────────────────────────────────────────────┘
```

Window B is what `Framework`'s docstring and `docs/architecture/kernel.md` invariant 9
describe. Window A is undocumented, wider (it lasts as long as teardown does), and silent.

Three facts from the current code shape the design:

1. **The kernel's own Window A reads are unaffected by anything on `Framework.resolve`.**
   `_components_for` binds `registry = self.registry` when the phase begins
   (`framework.py:504`), before `_reset` swaps the attribute. Hook dispatch reads through
   that bound object, not through `resolve`.
2. **`ashutdown` spawns no tasks.** `loader.ashutdown` awaits each step inline in the
   caller's own task (`loader.py:347-350`). Hook coroutines therefore run *in* the
   transition's task rather than in children of it.
3. **Teardown code has no route to the registry except the framework.** `teardown()` is
   invoked with no arguments (`loader.py:256-258`), and a shutdown hook receives only the
   components of *its own* module — `_components_for` groups by `(kind, namespace)`
   (`framework.py:513`). So teardown code needing anything it was not handed must reach a
   module-level framework, which is what the starter template binds
   (`starter/framework.py.tmpl:23`).

   The shipped starter does **not** itself exercise this: its `_close` hook iterates the
   `resources_of_app` it is passed. The `framework.resolve(...)` guidance in
   `starter/app/resources.py.tmpl:4-6` is addressed to surface code, at call time. So the
   exemption is justified by what the teardown signature makes *possible*, not by a shipped
   path that would break without it.

## Goals / Non-Goals

**Goals:**

- A read that arrives from outside an in-flight transition fails with its own error type,
  across both windows and both lifecycle paths.
- A read issued by the transition's own teardown code continues to succeed.
- The concurrency contract stops depending on attribute-store atomicity.
- Each surface gets a documented place to call shutdown from.

**Non-Goals:**

- **Draining readers.** The framework will not wait for, count, or block on in-flight
  readers. See the decision below.
- **Closing use-after-resolve.** A component the caller holds past the transition is the
  caller's; nothing short of leased/scoped resolution changes that, and that is an API
  redesign this change does not attempt.
- **A public "is it shutting down" predicate.** Adding one re-creates the check-then-act
  trap that `started` already sets; the answer is to attempt the read and catch.
- **Touching `Registry`.** It has no notion of a lifecycle and does not gain one.

## Decisions

### Core vs adapters, and where this lands

The refusal is **core behavior on the composition root**, not adapter behavior. `Framework`
owns the transition, so it owns the state that describes one. `Registry` stays a pure store:
it is constructed from a declaration, imports nothing, and "has no opinion about where
components came from". Dependency direction is unchanged — nothing new points outward, and
no external system is introduced, so no new adapter is required.

Surface-specific guidance (where to call shutdown from) is documentation against each
adapter, not code in the kernel.

### Decision: Reader draining — Adopt the host's drain

- **Status**: approved
- **Why**: The capability already exists one layer up and is guaranteed by contract there;
  acquiring a second one underneath it would wait for readers the host promises are gone.
- **Considered**: `readerwriterlock` 1.0.9 + `aiorwlock` (adopt — two runtime deps against
  the one-distribution mandate, a lock acquisition on every read, and a shutdown that can
  block on a slow reader); a hand-written epoch/generation counter (build — reader-tracking
  machinery in a kernel whose registry deliberately has no lifecycle notion).
- **Isolation**: No kernel code. The boundary is the surface adapter — the ASGI lifespan
  shutdown handler, or the call site after the RPC server's graceful stop returns —
  documented per surface in `ship-a-framework.md`.

The rejected options are mature and available, so this is a declined adoption rather than an
absence of options. Rejected on three grounds:

- It orders the *lookup* and not the *use*. `resolve` returns a component the caller then
  holds; a perfectly serialized lookup still hands back an object torn down a moment later.
  The expensive half of the hazard survives the expensive fix.
- `Microsoft.Extensions.DependencyInjection` shipped exactly this and withdrew it: resolving
  after disposal deadlocked, and .NET 6 RC1 replaced the synchronization with a thrown
  `ObjectDisposedException`, documented as a breaking change whose stated reason was "to fix
  the deadlock scenario". Spring reached the same place independently (`getBean` throws
  `IllegalStateException` after context close, asserted on the *context*, not the factory —
  which is also where this design puts the state).
- Hosts already drain. The ASGI lifespan spec sends `lifespan.shutdown` only once the server
  "has stopped accepting connections and closed all active connections"; gRPC's `stop(grace)`
  rejects new RPCs and grace-periods in-flight ones. A framework-level drain would wait for
  readers the host guarantees are already gone.

What the kernel owes is a straight answer, not an ordering it cannot enforce.

### Decision 2 — A distinct error, in the existing family

A new `SpocError` subclass meaning *the framework is transitioning*. Not a reuse of
`UnknownNamespaceError`: gRPC's taxonomy separates `NOT_FOUND` (permanent, caller's fault)
from `UNAVAILABLE` (transient, retryable, not the caller's fault), and SPOC currently reports
the second as the first. Subclassing `SpocError` keeps blanket handlers working; only a
handler catching `UnknownNamespaceError` specifically around a racing read changes behavior,
and that read was returning wrong answers.

Naming, tier, and message wording are implementation choices for `/opsx:apply`; the spec
requires only that the type be distinct, catchable, and in the family. It joins the published
surface with a tier stated where it is defined, per `public-api-surface`.

### Decision: Transition membership — Adopt `contextvars` (standard library)

- **Status**: approved
- **Why**: One `ContextVar` answers "am I inside the transition?" correctly on both lifecycle
  paths, because its isolation rules already match the two shapes SPOC needs — contexts are
  per-thread, and per-task via the copy taken at task creation.
- **Considered**: two discriminators, `_transition_owner` (thread ident) for the sync path
  plus a `ContextVar` for the async one (adopt — but two mechanisms satisfying one spec
  requirement, with the drift risk that implies); `threading.local()` alone (adopt — one
  mechanism, but wrong on the async path, where every task shares a thread and every racing
  task would be wrongly exempted).
- **Isolation**: Private state on `Framework`, set and reset by the `_transition` context
  manager. It never reaches `Registry`, and no caller sees it — membership is observable only
  through whether a read is served.

The refusal must exempt the transition's own teardown code — fact 3 above means refusing it
would leave teardown unable to reach anything it was not directly handed. This is precisely
ZeroMQ's shape: `ContextTerminated`
is raised by every socket operation after `ctx.term()`, "with the exception of
`socket.close()`" — a terminated-state error plus an explicit carve-out for the operation
teardown still needs. SPOC scopes its carve-out by transition membership rather than by
method name.

One mechanism covers both paths. `contextvars` isolation was verified against all four cases:

| Case | Reads | Outcome |
|---|---|---|
| Racing caller on another thread | `False` | refused — a new thread starts with an empty context |
| Racing task that predates the transition | `False` | refused — its context was copied before the marker was set |
| Teardown hook, awaited inline | `True` | exempt — same task, same context (fact 2) |
| Task spawned *by* teardown code | `True` | exempt — `create_task` copies the spawner's context, and work spawned by teardown *is* teardown |

The last row is the one worth stating explicitly, because it looks like a leak and is not:
context is inherited from whoever calls `create_task`, so only code already inside the
transition can propagate the marker. Unrelated code racing the shutdown sits in its own
context and is refused.

This is also PEP 567's stated purpose — a stateful context manager should carry its state in a
`ContextVar` rather than `threading.local()` precisely so it cannot bleed into concurrent
code — and `Framework._transition` is such a context manager.

### Decision 4 — Restate invariant 9 rather than extend it

Invariant 9 currently guarantees "one whole registry, never a torn state" on the strength of
attribute-store atomicity. Python's published thread-safety guarantees cover built-in types
and do not extend to attribute assignment on custom objects under free-threaded builds. With
the refusal in place the guarantee no longer rests on that detail, so the invariant should be
rewritten to state the draining ownership rather than patched to add a clause.

## Risks / Trade-offs

- **A residual window remains.** A read that passes the membership check one instruction
  before shutdown marks the transition still gets through. → Accepted and stated. It shrinks
  the hazard from the whole teardown duration to a single check, and the residue is in-flight
  work, which every graceful-shutdown standard assigns to the caller. The spec says so
  explicitly rather than implying totality.
- **A `ContextVar` must be reset, not merely set.** A marker left set after a transition would
  exempt every subsequent read on that thread or task. → Set and reset via the token in
  `_transition`'s existing `finally`, which already exists for `_transition_owner` and is
  where the unconditional-inert-state guarantee is enforced.
- **Work spawned by teardown inherits the exemption.** A task created by a shutdown hook is
  treated as inside the transition. → Correct by intent, not a leak (see the table above), but
  it means a hook that spawns long-lived work hands that work the exemption too. Recorded so
  it is a stated property rather than a surprise.
- **Teardown code that catches broad exceptions may swallow the new error.** → Message and
  type are explicit; a shutdown hook catching `SpocError` blanket-style is a pre-existing
  hazard this change does not widen.
- **The exemption is justified by a possible path, not a shipped one.** No template in the
  tree resolves during teardown today, so nothing existing regresses without it — but the
  teardown signature makes the pattern the only option for a hook needing a component from
  another app or kind. → Covered by a test that exercises the pattern directly, and the
  starter's own shutdown stays covered by its existing end-to-end test.

## Migration Plan

Additive: one new exported error, one new refusal on a path the contract declared uncovered.
No deprecation cycle is owed — nothing is withdrawn. `apidiff` should report an added public
name and no `violated:` line. Rollback is reverting the change set; no persisted state or
configuration is involved.

Sequence this **before** the 1.0 cut. 1.0 freezes the concurrency contract, and after it an
incomplete withdrawal fails in any increment.

### Decision: Scope of the refusal — all transitions, not shutdown only

- **Status**: approved
- **Why**: Start has the same two windows — discovery populates the registry incrementally,
  so a racing read sees a half-populated view, and a *failed* boot's rollback swaps the
  registry exactly as shutdown does. Covering shutdown only would leave the identical defect
  alive on the boot-failure path and require carving start out of a spec already written for
  transitions generally.
- **Considered**: shutdown-only (keeps today's boot behavior, but documents the boot-failure
  path as an uncovered case — the same asterisk this change exists to remove).
- **Isolation**: None needed — the membership predicate and the marker are already
  per-transition, so covering start is the absence of a carve-out rather than new machinery.

Everyone legitimate during a boot — app module code at import time, ready callbacks, startup
hooks, module `initialize()` — runs inline inside the transition and is exempt via the
marker; for all of them the refusal changes nothing. The one pattern that changes: an
`initialize()`-spawned **worker thread** that resolves immediately. Today it succeeds against
the complete registry; under the refusal it is refused until start completes. That pattern
was silently unsafe — it races a boot that can still fail and roll back under it — and the
remedy is to resolve inside `initialize()` (exempt) and hand the object to the thread. An
asyncio *task* spawned by `initialize()` inherits the context and stays exempt; only threads
are affected, because threads start with a fresh context (verified).

Explicitly out of scope: a **never-started** framework still answers with unknown-segment
errors against its empty registry. That is deterministic misuse, not a race; changing it
would drag in surfaces that legitimately construct frameworks without starting them, and it
is severable from this change if it is ever wanted.

## Open Questions

- **Naming.** The error's name should read well at a call site and next to `UnknownKindError`
  and friends. `/opsx:apply` decides.
- **Could `_transition_owner` fold into the marker?** It survives this change because it
  answers a different question — reentrancy ("is *this thread* already in a transition?")
  rather than membership ("is this caller inside one?"). But the `ContextVar` answers
  reentrancy too, and answers it correctly on the async path where thread identity cannot:
  a ready callback calling `start` from a task would currently be caught only because it
  shares a thread. Folding them would change tested reentrancy behavior, so it is severable
  from this change and worth its own look.
- ~~**Tier for the new error.**~~ Settled during apply: `derive_tier` assigns `public` to
  anything exposed from the package without a provisional notice, so the export *is* the
  declaration. `apicheck` passes and `apidiff` reports it as `added: ... (public)`.
