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

#### Scenario: Inside and outside are distinguished on both paths

- **WHEN** a shutdown is in flight and two reads arrive — one issued by a
  teardown the shutdown itself invoked, one issued by an unrelated concurrent
  caller — on either the synchronous or the asynchronous path
- **THEN** the framework classifies the first as inside the transition and the
  second as outside it, and does so identically on both paths

## ADDED Requirements

### Requirement: A read arriving from outside an in-flight transition MUST be refused

A resolution request that arrives from outside an in-flight lifecycle transition MUST fail
with an error stating that the framework is transitioning. The refusal MUST cover the whole
transition — both while teardown work is running and after the registry has been returned
to its inert state — so that no read spanning the window can succeed against components
whose teardown has already run.

The refusal MUST NOT be reported as a resolution failure of any identifier segment. An
identifier that would resolve when the framework is settled MUST NOT be answered as though
its kind, namespace, or object name were unknown.

The error MUST be distinguishable by type, not only by message, so a caller can catch it
without inspecting text, and MUST be a member of the framework's existing error family.

#### Scenario: Read during teardown

- **WHEN** a shutdown is in flight, teardown work is still running, and an unrelated caller
  resolves an identifier that was registered before the shutdown began
- **THEN** the read fails with the transitioning error rather than returning the component

#### Scenario: Read after the registry is reset

- **WHEN** a shutdown has reset the registry but the transition has not completed, and an
  unrelated caller resolves an identifier that was registered before the shutdown began
- **THEN** the read fails with the transitioning error, and not with an unknown-segment error

#### Scenario: A genuine typo is still a segment failure

- **WHEN** no transition is in flight and a caller resolves an identifier whose namespace
  was never registered
- **THEN** the read fails with the unknown-namespace error, naming the segment and the
  candidates, exactly as before

#### Scenario: Reads are unaffected once settled

- **WHEN** the framework has completed a start and no transition is in flight
- **THEN** resolution behaves exactly as it does today, with no additional failure mode
  and no coordination required of the caller

### Requirement: Teardown code MUST still resolve during its own transition

A resolution request issued from inside an in-flight transition MUST be served normally
against the registry as it stands at that moment. Shutdown hooks and module teardown
functions are the reason the populated registry outlives the start of a shutdown; refusing
their reads would make the teardown phase unable to reach the components it exists to tear
down.

This exemption MUST be scoped to the in-flight transition. It MUST NOT be a general
suspension of the refusal that any concurrent caller could benefit from, and it MUST end
when the transition ends.

#### Scenario: A teardown resolves a component

- **WHEN** a module's teardown function resolves an identifier while the shutdown that
  invoked it is in flight
- **THEN** the read succeeds and returns the registered component

#### Scenario: The exemption does not leak to other callers

- **WHEN** a teardown function is mid-execution and an unrelated concurrent caller resolves
  an identifier at the same moment
- **THEN** the teardown's read succeeds and the unrelated caller's read fails with the
  transitioning error

#### Scenario: The exemption ends with the transition

- **WHEN** a shutdown has completed and a caller resolves any identifier
- **THEN** the read is no longer exempt, and the framework answers as an inert framework
  answers

### Requirement: Draining in-flight readers MUST remain outside the framework's responsibility

The framework MUST NOT wait for, track, or block on in-flight readers as part of a
transition. Ordering readers against a shutdown belongs to the host that admitted the work —
the surrounding server, transport, or supervising loop — which alone knows what a unit of
work is and when one has finished.

The framework's obligation is bounded and MUST be stated as such: it serializes transitions
against each other, and it answers a read honestly whether or not the caller ordered itself
correctly. It does not make an unordered caller correct. A resolved component that a caller
holds past the end of a transition MUST remain the caller's responsibility, because the
framework never observes the use of what it returned.

#### Scenario: A shutdown does not block on a reader

- **WHEN** a shutdown is invoked while another caller is repeatedly resolving identifiers
- **THEN** the shutdown proceeds and completes without waiting for that caller to stop, and
  the reader's requests fail with the transitioning error rather than delaying the shutdown

#### Scenario: A host that drains first sees no refusals

- **WHEN** a host finishes every unit of work it admitted before invoking shutdown
- **THEN** no read races the transition, no transitioning error is raised, and the
  framework's refusal never becomes observable

#### Scenario: A component held past the transition

- **WHEN** a caller resolves a component before a shutdown begins and then uses it after the
  shutdown has completed
- **THEN** the framework neither prevents nor reports this, and the contract states that
  ordering the use is the caller's responsibility
