## ADDED Requirements

### Requirement: A busy transition MUST be refused by the asynchronous path, never waited for

The asynchronous lifecycle path MUST report a transition already in progress immediately,
without waiting for the in-flight transition to settle. Where the synchronous path may
block until the transition it is serialized against completes, the asynchronous path MUST
NOT: a caller that awaits an asynchronous start or shutdown while another transition holds
the framework MUST receive the already-in-progress failure, and the work it shares its
execution context with MUST continue to make progress meanwhile.

This is distinct from, and stronger than, the existing prohibition on deadlock. A path
that waits for a lock it will eventually obtain does not deadlock, and would satisfy every
other requirement here while still stalling every unrelated task the caller is running —
the failure mode that matters to anyone embedding an asynchronous start in a server's
startup, where the transition it waits on may be seconds of module imports and hook
dispatch.

The refusal MUST remain distinguishable from the reentrant case, per *Lifecycle
transitions are serialized*: a caller refused for a busy framework may retry once the
transition settles, and one refused for reentrancy never can.

#### Scenario: A racing asynchronous transition is refused rather than queued

- **WHEN** an asynchronous start is awaited while another transition on the same framework
  is in flight
- **THEN** it fails with the already-in-progress error before that transition settles, and
  the error is the racing one rather than the reentrant one

#### Scenario: Unrelated work continues while the transition is refused

- **WHEN** a caller awaits an asynchronous start that is refused for a busy framework,
  concurrently with other scheduled work
- **THEN** that other work runs to completion without being delayed until the in-flight
  transition settles
