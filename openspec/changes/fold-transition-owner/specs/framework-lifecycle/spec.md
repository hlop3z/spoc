## MODIFIED Requirements

### Requirement: Lifecycle transitions are serialized

Concurrent invocations of start and shutdown MUST be serialized against each
other and against themselves. When multiple callers race to start the same
framework, exactly one start proceeds; every other caller fails with the
already-started error. A shutdown racing a start MUST observe either the
fully-started or the fully-inert state, never a partial boot.

A lifecycle transition invoked from inside an in-flight transition — a ready
callback, lifecycle hook, or module initializer calling start or shutdown on
the framework that is mid-transition — MUST fail immediately with an error
naming the reentrant call. It MUST NOT deadlock, on either lifecycle path.

A transition is a window with an inside and an outside, and the framework MUST
be able to tell them apart. Work invoked by the transition itself — a shutdown
hook, a module teardown, anything they call in turn — is inside it. Every other
caller is outside it. The distinction MUST hold identically on the synchronous
and asynchronous lifecycle paths.

Whether a caller is inside a transition MUST be one determination, applied
identically to a read and to a further transition. A caller is inside a
transition when the transition invoked it, directly or through work it spawned;
membership MUST NOT be inferred from which execution context the caller happens
to share with the transition, because concurrent work can share one and
transition-spawned work can fail to.

A transition invoked from outside an in-flight transition MUST be reported as a
transition already in progress, distinctly from the reentrant case, on both
lifecycle paths. Reporting a concurrent caller as reentrant is a defect: the two
have opposite remedies — a concurrent caller may retry once the transition
settles, a reentrant one never can.

#### Scenario: Racing starts

- **WHEN** two threads invoke start on the same framework concurrently
- **THEN** exactly one start succeeds, the other fails stating the framework
  is already started, and every discovered component is present in the
  registry exactly once

#### Scenario: Reentrant transition from lifecycle code

- **WHEN** a startup hook or ready callback invokes shutdown (or start) on the
  framework that is currently mid-start
- **THEN** that inner call fails immediately with an error naming the
  reentrant transition, no deadlock occurs, and the outer start fails with
  that error and rolls back as any hook failure does

#### Scenario: Concurrent transition is not reported as reentrant

- **WHEN** a transition is in flight on the asynchronous path and an unrelated
  caller that the transition did not invoke — one that predates it and merely
  shares its execution context — invokes start or shutdown on the same
  framework
- **THEN** the call fails immediately stating a transition is already in
  progress, and does not state that it was called from inside a transition

#### Scenario: Work the transition spawned is inside it

- **WHEN** a lifecycle hook on the asynchronous path spawns a concurrent task
  and that task invokes start or shutdown on the framework whose transition
  spawned it
- **THEN** the call fails immediately with the reentrant-transition error,
  because work a transition spawns inherits its membership

#### Scenario: Inside and outside are distinguished on both paths

- **WHEN** a shutdown is in flight and two reads arrive — one issued by a
  teardown the shutdown itself invoked, one issued by an unrelated concurrent
  caller — on either the synchronous or the asynchronous path
- **THEN** the framework classifies the first as inside the transition and the
  second as outside it, and does so identically on both paths
