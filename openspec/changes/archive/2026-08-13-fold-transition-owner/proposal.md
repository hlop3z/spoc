## Why

The framework decides "is this caller reentering a transition?" with thread identity, but
decides "is this caller inside a transition?" with a context marker. Two mechanisms answer
one question, and on the asynchronous path the thread-identity one answers it wrongly: an
unrelated task sharing the event loop thread is indistinguishable from lifecycle code
calling back into the framework, so a racing caller is told it reentered. The diagnosis is
wrong, and the caller's correct response — retry once the transition settles — is exactly
the one the message argues against.

Now, because the 1.0 cut freezes the concurrency contract this sits inside. After the
freeze, correcting which error a racing async caller receives is a breaking change gated
to a major release.

## What Changes

- Reentrancy is decided by the same inside/outside test the framework already applies to
  reads, so both questions are answered by one mechanism whose isolation rules match both
  lifecycle paths.
- A concurrent transition arriving from outside an in-flight one is reported as a
  transition already in progress on both paths. Today the asynchronous path reports it as
  reentrancy. **BREAKING** for anyone matching on that message text; the error type is
  unchanged, and the pre-1.0 allowance covers it.
- Work the transition itself spawned — an inline await, a task a hook created — remains
  inside the transition and is still refused as reentrant.
- The reentrancy message stops asserting the call came from the same thread, which is no
  longer what is tested and was never what made the call wrong.
- No public name is added, removed, or retyped.

## Capabilities

### New Capabilities

None. This narrows an existing contract; it introduces no new one.

### Modified Capabilities

- `framework-lifecycle`: the serialization requirement gains the rule that reentrancy and
  read-membership are decided by one and the same inside/outside test, and that a
  transition arriving from outside an in-flight one is reported as concurrent rather than
  reentrant — identically on the synchronous and asynchronous paths.

## Impact

- `src/spoc/framework.py` — `_refuse_reentry`, `_begin_transition`, `_end_transition`, and
  the `_transition_owner` attribute; the class docstring paragraph describing reentrancy.
- `tests/test_framework.py` — the two existing reentrancy tests keep passing unchanged
  (both are synchronous inline calls); the asynchronous cases that change are untested
  today and gain coverage.
- `docs/architecture/kernel.md` — invariant 9 describes the concurrency contract and
  mentions the mechanisms.
- No dependency, no packaging, and no public API change. Sequenced before the 1.0 cut.
