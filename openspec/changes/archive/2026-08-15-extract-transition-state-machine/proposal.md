## Why

`framework.py` is 785 lines and the only file in `src/` above the 600-line review
threshold in `.canon/guidelines.md`. Of those, `Framework` itself is one class of 31
methods spanning four distinct jobs: declaring kinds, discovering and registering apps,
resolving reads, and arbitrating lifecycle transitions.

The fourth is the one that does not belong. Transition arbitration is a small state
machine — a lock, an in-flight label, and a context marker — whose correctness argument
is entirely about concurrency and is entirely independent of what a framework *is*. It is
also the part with the most subtle invariant in the kernel: whether a caller is inside a
transition must be one determination applied identically to a read and to a further
transition, and getting it wrong reports a concurrent caller as reentrant, which have
opposite remedies. That argument is currently interleaved with app discovery and kind
declaration, so a reader checking it has to hold the rest of `Framework` in their head.

Now, because the extraction is invisible from outside — every member involved is private
and `spoc.core` is already declared internal — so it costs nothing at any release, and
1.0 is the last moment it can land without a version's worth of noise around it.

## What Changes

- The transition state machine moves out of `Framework` into its own kernel module: the
  `_active_transitions` context variable, the lock and the in-flight label, and the
  members that read and write them (`_refuse_racing_read`, `_refuse_reentry`,
  `_begin_transition`, `_end_transition`, `_inside_transition`, and the `_transition`
  context manager).
- `Framework` keeps every entry point it has today and delegates arbitration to the
  extracted collaborator. Both lifecycle paths keep their current acquisition
  behavior — the synchronous one through a context manager, the asynchronous one
  acquiring without blocking so a racing transition is reported rather than awaited.
- `docs/architecture/kernel.md` gains the collaborator and the boundary it sits on
  (Rule 1).
- No public API change, no behavior change, no **BREAKING** change. Nothing named here is
  exported, and `spoc.core` carries no stability promise.

## Capabilities

### New Capabilities

None. This change introduces no observable behavior.

### Modified Capabilities

- `framework-lifecycle`: adds one requirement — the asynchronous path MUST refuse a busy
  framework rather than wait for it.

Almost every requirement governing this machinery is already stated there — *Lifecycle
transitions are serialized*, *A read arriving from outside an in-flight transition MUST be
refused*, *Teardown code MUST still resolve during its own transition*, *Draining
in-flight readers MUST remain outside the framework's responsibility*, and *Asynchronous
lifecycle path*. This change moves where those are implemented, not what they require, and
they are the acceptance criteria: they must pass unchanged, against the same tests, before
and after.

**One is missing, and scoping this change is what surfaced it.** The asynchronous path
takes the lock without blocking so a racing transition is refused rather than awaited.
The spec requires only that it MUST NOT deadlock — which a blocking acquire also
satisfies, since it does eventually obtain the lock. So the property is currently held by
nothing but two open-coded `blocking=False` calls and a docstring, and consolidating those
two call sites into one collaborator could quietly drop it while every existing test still
passed: a racing asynchronous transition is rare in tests, and blocking briefly still
yields the correct final state. It would fail only in production, in the case it exists
for — an asynchronous start embedded in a server's startup, parking the event loop for
however long the in-flight transition takes.

The requirement is therefore added **before** the code moves, so the refactor has an
acceptance criterion for the one property it is most able to break invisibly.

## Impact

- **Code**: `src/spoc/framework.py` (shrinks below the review threshold), one new module
  under `src/spoc/core/`.
- **Tests**: none rewritten. `tests/test_transition_reads.py`, `tests/test_concurrency.py`,
  and `tests/test_async_lifecycle.py` exercise this machinery through `Framework`'s public
  entry points and must pass untouched — that is what makes the refactor verifiable.
- **Docs**: `docs/architecture/kernel.md`.
- **API surface**: unchanged. `apicheck` and `apidiff` must report no delta.
- **Dependencies**: none. The machinery uses `threading` and `contextvars` from the
  standard library and continues to.
