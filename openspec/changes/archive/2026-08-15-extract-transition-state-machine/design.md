## Context

`Framework` arbitrates lifecycle transitions with three pieces of state and six members
that read or write them:

| Piece | Today |
| --- | --- |
| `_active_transitions` | Module-level `ContextVar[frozenset[Framework]]` — who is *inside* a transition |
| `_transition_lock` | Instance `threading.Lock` — serializes concurrent transitions |
| `_transitioning` | Instance `str \| None` — the label of the transition in flight, or settled |

Read by `_refuse_racing_read`, `_refuse_reentry`, `_inside_transition`; written by
`_begin_transition`, `_end_transition`, and the `_transition` context manager.

Four entry points drive it, and they split into two acquisition styles:

- `start` / `shutdown` take the lock through `_transition`, blocking until it is free.
- `astart` / `ashutdown` open-code the same sequence with `acquire(blocking=False)`,
  because parking an event loop on a lock is not an option. Each repeats the reentry
  refusal, the acquire, the begin, and a two-statement `finally` — and each spells the
  same `"Framework lifecycle transition already in progress"` literal.

That duplication is the immediate cost. The structural cost is that the concurrency
argument — a caller is *inside* a transition when the transition invoked it, which is what
separates a reentrant caller (never retryable) from a racing one (retryable once settled)
— sits interleaved with kind declaration and app discovery in one 785-line file.

## Goals / Non-Goals

**Goals:**

- Move the transition state machine into one unit that owns all three pieces of state, so
  the concurrency argument can be read without reading `Framework`.
- Collapse the two open-coded asynchronous sequences into the same unit the synchronous
  paths use, leaving one place where the marker is set and one where it is cleared.
- Bring `framework.py` under the 600-line review threshold in `.canon/guidelines.md`.
- Keep every requirement in `framework-lifecycle` passing against its existing tests,
  unmodified. That is the acceptance criterion.

**Non-Goals:**

- No change to what any lifecycle path does, in what order, or which error it raises.
- No new public API. Nothing here is exported; `spoc.core` carries no stability promise.
- No change to reentrancy or racing semantics, and no attempt to make the asynchronous
  path block — its non-blocking acquire is a deliberate property, not an oversight.
- No async lock. The lock guards a synchronous critical section on the calling thread;
  `asyncio.Lock` would change what "concurrent" means and is out of scope.

## Decisions

### A collaborator object, not a mixin or free functions

`Framework` composes a gate — `self._transitions = TransitionGate()` — and delegates.

*Alternatives considered.* A **mixin** would shrink the file while leaving all three
pieces of state on `Framework` and its method count unchanged in practice; inheritance
would hide the very boundary the change exists to draw. **Free functions over state still
owned by `Framework`** would move the code without moving the responsibility, so the
invariant would still be argued across two modules. A collaborator owns the state and the
rules over it together, which is what makes the unit readable alone.

### Membership is keyed by the gate, not by the framework

`_active_transitions` becomes `ContextVar[frozenset[TransitionGate]]`. One gate belongs to
exactly one framework, so membership semantics are identical — and the context variable
stops needing a forward reference to `Framework`, which is what lets the module stand on
its own. Nesting still works for the same reason it does today: the marker is a set, so a
startup hook that boots a second framework adds a second gate without displacing the
first, and reads on the outer one stay inside their own transition.

### Two named entries over one flag

The gate exposes two context managers rather than `hold(label, blocking=...)`:

- `hold(label)` — blocks for the lock. Used by `start` / `shutdown`.
- `claim(label)` — takes the lock or raises immediately. Used by `astart` / `ashutdown`.

Both delegate to one implementation, so the begin/end pairing is written once. Two names
because the caller is choosing a *failure mode*, not tuning a parameter: a boolean at the
call site reads as configuration, where the choice is actually which of two documented
behaviors the path requires. `framework-lifecycle` distinguishes these outcomes normatively
on both paths, so the code that implements them should be distinguishable by name.

A synchronous context manager is correct on the asynchronous path: entry and exit both run
in the coroutine's own context, which is exactly what the current hand-written
`try/finally` already relies on for the context variable to reset correctly.

### Read refusal moves with the state it reads

`refuse_racing_read(identifier)` moves onto the gate and keeps raising
`FrameworkTransitioningError`. It reads `_transitioning` and membership and nothing else,
so leaving it on `Framework` would leave a reader of gate state outside the gate — the
split this change exists to remove. The four read accessors call
`self._transitions.refuse_racing_read(identifier)` in place of the current private call.

### Placement and dependency direction

The unit lands at `src/spoc/core/transition.py`, beside the other kernel modules.
Dependencies point inward and acquire no cycle:

```
framework.py  ──imports──▶  core/transition.py  ──imports──▶  core/exceptions.py
```

`core/exceptions.py` already defines both errors the gate raises (`SpocError`,
`FrameworkTransitioningError`) and imports nothing from `framework.py`.

### Build-vs-adopt

One concern here is correctness-sensitive — transition arbitration under concurrency — and
it is **already adopted, not built**: `threading.Lock` and `contextvars.ContextVar` are the
standard library's, and this change moves the code that calls them without replacing
either. No new dependency, no hand-rolled primitive, so `/ai:decide` records no new ADR.
The alternative worth naming and rejecting is an async-aware lock library: it would make
the asynchronous path block where today it refuses, changing observable behavior this
change forbids itself from touching.

## Risks / Trade-offs

- **A context-variable token leaks or resets in the wrong context** → the worst outcome in
  this change: every later read on that thread or task is exempted and every later
  transition looks reentrant. Mitigated by having exactly one implementation set and reset
  the token — fewer places than today's four — and by `tests/test_transition_reads.py`,
  which pins refusal from outside and permission from inside.
- **Delegation is mistaken for indirection** → one more hop from `resolve` to the refusal.
  Accepted: the hop buys a unit whose correctness can be argued without `Framework`, and
  the read accessors already made a private call at exactly this point.
- **The refactor changes behavior invisibly** → mitigated by the constraint that no test is
  rewritten. `test_transition_reads.py`, `test_concurrency.py`, and `test_async_lifecycle.py`
  drive this machinery through public entry points and must pass untouched; a test that
  needed editing would be evidence the change did more than it claims.
- **One gate per framework becomes an assumption someone breaks** → if a second gate were
  ever attached to one framework, membership would silently split. Mitigated by
  constructing it in `Framework.__init__` and nowhere else, and by the gate holding no
  back-reference that would invite reuse.

## Migration Plan

None required. No published name moves, no persisted state, no configuration. The change
is a single commit that is either present or absent; rollback is `git revert`.
