## Why

A read that races shutdown is answered wrongly, in two different ways, and the caller
cannot tell either time. While teardown runs, `resolve` still succeeds and hands back a
component whose shutdown hook has already fired — no error, no signal. After the registry
is swapped, `resolve` fails as an unknown-namespace error, which is exactly what a typo
produces. The concurrency contract currently declares this window uncovered, which was a
fair position at 0.x; 1.0 freezes that contract, and freezing it means promising that an
unknown-namespace error means an unknown namespace.

## What Changes

- **A read arriving during a lifecycle transition is refused, with its own error.** The
  framework gains a distinct failure meaning *this framework is shutting down*, separate
  from every failure meaning *that name does not exist*. It covers both halves of the
  window: the teardown phase and the post-swap phase.
- **Teardown code is exempt.** A read issued from inside the in-flight transition —
  a shutdown hook, a module `teardown()` — still resolves. This is not a nicety:
  `teardown()` is invoked with no arguments, and a shutdown hook receives only its own
  module's components, so teardown code needing anything beyond what it was handed has
  no route except the framework. Refusing those reads would make the teardown phase
  unable to reach parts of the registry it exists to tear down.
- **The contract names who owns the drain, and it is not the kernel.** Waiting for
  in-flight readers is the transport's job — the ASGI lifespan protocol closes every
  connection before it sends `lifespan.shutdown`, and gRPC rejects new RPCs and grace-periods
  the rest before `stop()` returns. The kernel serializes transitions and answers reads
  honestly; it does not acquire a second drain underneath one that already ran.
- **Behavior change on a previously-uncovered path.** A caller catching the
  unknown-namespace error specifically, around a read that races shutdown, stops catching
  it. That path is currently documented as outside the contract and currently returns
  wrong answers, so this is a correction rather than a withdrawal — but it is a visible
  change and the release gate should see it as one.
- **The concurrency invariant stops resting on an undocumented detail.** It currently
  guarantees "one whole registry, never a torn state" on the strength of attribute-store
  atomicity, which Python's own thread-safety guarantees do not extend to custom objects
  under free-threaded builds. With the refusal in place the guarantee no longer depends
  on it.

## Capabilities

### New Capabilities

None. Every change lands on an existing capability; introducing a new one would split the
lifecycle contract across two specs.

### Modified Capabilities

- `framework-lifecycle`: the serialized-transitions requirement gains a draining state.
  A transition is a window with an inside and an outside — reads from outside it are
  refused, reads from inside it (teardown code) are served — and the requirement states
  that draining in-flight readers is the surrounding transport's responsibility, not the
  framework's.
- `component-resolution`: the failures-name-the-failing-segment requirement gains the
  distinction it is currently missing. An unavailable framework and an absent name are
  different conditions and MUST raise different errors; a segment error means the segment.
`public-api-surface` is deliberately **not** modified. The new error is one more element
governed by its existing requirements — it needs a tier stated where it is defined, and the
surface check must see it — but no requirement there changes. That spec says nothing about
concurrency, so the shutdown window was never one of its stated exclusions.

### Critical concerns for `/ai:decide`

- **Transition membership** — how a read determines whether it originates inside the
  in-flight transition. Correctness-sensitive: the synchronous and asynchronous paths do
  not share a discriminator, because the async path runs hooks in the caller's own task
  rather than spawning any, so thread identity cannot separate a teardown read from a
  racing task on the same event loop.
- **Reader draining** — whether the kernel acquires any mechanism for waiting on in-flight
  readers. The recommendation is to adopt none and delegate to the transport; the decision
  is recorded because the alternative is what `Microsoft.Extensions.DependencyInjection`
  shipped and then withdrew as a deadlock.

## Impact

- `src/spoc/core/exceptions.py` — one new member of the error family.
- `src/spoc/framework.py` — transition state, the read-path refusal, the exemption, and
  the concurrency docstring.
- `src/spoc/__init__.py` — the new error joins the published surface, with a tier.
- `src/spoc/core/registry.py` — **deliberately untouched.** The registry has no notion of
  a lifecycle and must not gain one; the state belongs to the framework that owns the
  transition.
- `docs/architecture/kernel.md` — invariant 9 restated.
- `docs/docs/how-to/ship-a-framework.md` — where to call shutdown from, per surface
  (ASGI lifespan handler, after `server.stop(grace)`, and the cases with no ambient drain:
  ZeroMQ loops, app-spawned background tasks, worker threads, CLIs).
- `docs/docs/api/stability.md` — the new element and its tier.
- Tests — both windows, both lifecycle paths, and the teardown exemption.
- Release gate — `apidiff` sees an added public name; the behavior change is on a path the
  contract declared uncovered.
