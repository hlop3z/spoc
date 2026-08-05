# Framework Lifecycle — delta

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

### Requirement: Hooks receive an ordered, immutable component collection

A kind's startup and shutdown hooks MUST receive the components of that kind belonging
to the module's app as an immutable collection in the registry's canonical enumeration
order — ordered by canonical identifier, the same order registry enumeration yields.
Two starts of the same project MUST hand every hook its components in the same order.

Hook dispatch is per loaded module: a kind's hooks fire once for each loaded app module
of that kind, receiving the components that app contributed. Components registered
without a backing app module — configured registrations — do not, by themselves, cause
hooks to fire, and this dispatch rule MUST be stated in the lifecycle documentation
rather than left for the author to discover from a hook that never ran.

#### Scenario: Hook payload order is canonical identifier order

- **WHEN** an app module declares several components of a hooked kind and start runs
- **THEN** the startup hook receives exactly those components, ordered by their
  canonical identifiers

#### Scenario: Hook payload is immutable

- **WHEN** a startup hook attempts to mutate the collection it receives
- **THEN** the mutation fails, and the registry is unaffected

#### Scenario: A kind populated only by configured registrations fires no hooks

- **WHEN** a kind declaring lifecycle hooks is populated solely through configured
  registrations and start runs
- **THEN** no hook fires for that kind, and the lifecycle documentation states this
  dispatch rule explicitly

### Requirement: Asynchronous lifecycle path

The framework MUST offer an asynchronous start and an asynchronous shutdown
whose observable behavior equals the synchronous ones. Kind lifecycle hooks
and module initialize/teardown functions declared as coroutine functions MUST
be awaited by the asynchronous path. The synchronous path MUST fail loudly,
naming the offending hook or module, when it encounters a coroutine it cannot
run — it never skips one and never half-runs it.

Only hook dispatch and module initialize/teardown are awaited: discovery —
configuration reads and module imports — is synchronous work on both paths,
and the asynchronous path's documentation MUST state this so callers embedding
start in a server's startup do not assume discovery yields to the event loop.

#### Scenario: Async start awaits coroutine hooks

- **WHEN** a kind declares a coroutine startup hook and the asynchronous start
  is awaited
- **THEN** the hook is awaited to completion before start returns, and the
  framework reports started

#### Scenario: Sync start refuses coroutine hooks

- **WHEN** a kind declares a coroutine startup hook and the synchronous start
  is invoked
- **THEN** start fails with an error naming the hook and directing the caller
  to the asynchronous path, and the framework returns to its inert state

#### Scenario: Async shutdown awaits coroutine teardown

- **WHEN** a module declares a coroutine teardown and the asynchronous
  shutdown is awaited after an asynchronous start
- **THEN** the teardown is awaited to completion in reverse dependency order

#### Scenario: The synchronous-discovery contract is stated

- **WHEN** the asynchronous path's documentation is consulted
- **THEN** it states that discovery is synchronous and only hooks and module
  lifecycle functions are awaited

## ADDED Requirements

### Requirement: Hook pairing is symmetric under a failed boot

When a boot fails partway, every module whose kind startup hook has fired MUST have its
kind shutdown hook fired during rollback, whether or not that module's own initialize
completed. Rollback MUST never leave a fired startup hook without its paired shutdown
hook.

#### Scenario: Initialize failure still pairs the hooks

- **WHEN** a module's initialize raises after its kind's startup hook has fired
- **THEN** rollback fires that kind's shutdown hook for that module before start's
  failure escapes, and the framework returns to its inert state
