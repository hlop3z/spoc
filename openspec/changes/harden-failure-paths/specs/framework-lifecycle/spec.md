## ADDED Requirements

### Requirement: Reaching the inert state is unconditional

The framework MUST reach its inert state whenever a transition out of the started state is
attempted, whether or not the app-authored code that transition invokes succeeds, and
whether or not the rollback of a failed boot itself succeeds. Inert means everything the
kernel owns is reset — the registry, module-ordering bookkeeping, and loaded configuration
— and a subsequent start is accepted.

A failure raised by app-authored lifecycle code still propagates unwrapped; reaching the
inert state is owed *in addition to* propagating, never instead of it. Where both a
teardown failure and a rollback failure occur, the failure the caller sees MUST be the one
the app authored, not one raised while cleaning up after it.

The guarantee is symmetric between the synchronous and asynchronous paths, and a framework
left inert by a failed transition MUST be restartable — it MUST NOT report itself started,
and it MUST NOT refuse a subsequent start on the grounds that a transition is still in
progress or already complete.

#### Scenario: A failing teardown still leaves the framework restartable

- **WHEN** a module's teardown raises during shutdown
- **THEN** shutdown fails with that exact error, the framework reports itself not started,
  every piece of kernel-owned state has been reset, and a subsequent start succeeds

#### Scenario: A failing shutdown hook still leaves the framework restartable

- **WHEN** a kind's shutdown hook raises during shutdown
- **THEN** shutdown fails with that exact error, the framework reaches its inert state, and
  a subsequent start succeeds

#### Scenario: Repeated shutdown after a failed shutdown does not re-run teardown

- **WHEN** shutdown is invoked a second time after a shutdown whose teardown raised
- **THEN** the call is the harmless no-op that shutting down a framework that never started
  is, rather than re-raising the same teardown failure

#### Scenario: A failure during rollback does not strand kernel state

- **WHEN** a boot fails and the rollback that follows also fails
- **THEN** the framework still reaches its inert state, and the failure that escapes to the
  caller is the one that failed the boot rather than the one raised during rollback

#### Scenario: The asynchronous path gives the same guarantee

- **WHEN** an asynchronous shutdown's awaited teardown raises
- **THEN** the framework reaches its inert state and a subsequent asynchronous start
  succeeds, exactly as on the synchronous path

## MODIFIED Requirements

### Requirement: App-authored lifecycle failures propagate unwrapped

A failure raised by app-authored lifecycle code MUST reach the caller as the exception
the app code raised, carrying its original type and traceback. App-authored lifecycle
code means a kind's startup or shutdown hook, or a module's initialize or teardown
function. The kernel MUST NOT wrap the failure in a kernel error or flatten it into a
message string. Failures the kernel itself
authors (ordering violations, coroutine refusal, configuration errors) remain kernel
errors. Start's rollback contract is unchanged: an app-authored failure during start
still tears down what came up and returns the framework to its inert state before the
exception escapes. Shutdown carries the same obligation: an app-authored failure during
shutdown returns the framework to its inert state before the exception escapes, so
propagating the failure and reaching the inert state are never traded off against each
other on either transition.

#### Scenario: Module initialize raises

- **WHEN** a module's initialize function raises an application-defined error during
  start
- **THEN** start fails with that exact error type and traceback, no kernel wrapper
  appears in the exception chain above it, and the framework is returned to its inert
  state

#### Scenario: Shutdown hook raises

- **WHEN** a kind's shutdown hook raises an application-defined error during shutdown
- **THEN** shutdown fails with that exact error, not a kernel error naming it, and the
  framework is returned to its inert state

#### Scenario: Kernel failures remain kernel errors

- **WHEN** the synchronous path encounters a coroutine hook it cannot run
- **THEN** the failure is a kernel error, exactly as the asynchronous-lifecycle
  requirement states

### Requirement: Restart rebuilds kernel state, not module state

After any shutdown attempt the framework MUST reset everything the kernel owns (the
registry, module-ordering bookkeeping, and loaded configuration), and a
subsequent start MUST rebuild the registry by re-running discovery. A shutdown whose
app-authored teardown failed is still a shutdown attempt for this purpose: the reset is
owed on the failing path exactly as on the succeeding one. The
contract MUST state that the language runtime's module cache and any
module-level state persist across restarts: module-level code executes at
most once per process, and the kernel makes no claim of reloading it.

#### Scenario: Restart re-registers from cached modules

- **WHEN** a framework starts, shuts down, and starts again in one process
- **THEN** the second start succeeds, the registry again contains every
  discovered component, and module-level side effects (such as an import-time
  counter) have occurred exactly once

#### Scenario: Restart after a failed shutdown re-registers identically

- **WHEN** a framework starts, a shutdown fails because a teardown raised, and a start is
  invoked again in the same process
- **THEN** the second start succeeds and the registry again contains every discovered
  component, indistinguishable from a restart after a clean shutdown

### Requirement: Asynchronous lifecycle path

The framework MUST offer an asynchronous start and an asynchronous shutdown
whose observable behavior equals the synchronous ones. Kind lifecycle hooks
and module initialize/teardown functions declared as coroutine functions MUST
be awaited by the asynchronous path. The synchronous path MUST fail loudly,
naming the offending hook or module, when it encounters a coroutine it cannot
run — it never skips one and never half-runs it.

The synchronous path's refusal MUST be a precondition rather than a discovery made partway
through: it MUST establish that no lifecycle code it is about to run is a coroutine before
it invokes any of it, so a coroutine declared by the last module to be walked refuses
before the first module's lifecycle code has run. The refusal names every offending hook or
module it found, not only the first.

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

#### Scenario: The refusal precedes every lifecycle side effect

- **WHEN** the last module in load order declares a coroutine initialize and the
  synchronous start is invoked
- **THEN** start fails without having run any earlier module's initialize or any kind's
  startup hook

#### Scenario: Async shutdown awaits coroutine teardown

- **WHEN** a module declares a coroutine teardown and the asynchronous
  shutdown is awaited after an asynchronous start
- **THEN** the teardown is awaited to completion in reverse dependency order

#### Scenario: The synchronous-discovery contract is stated

- **WHEN** the asynchronous path's documentation is consulted
- **THEN** it states that discovery is synchronous and only hooks and module
  lifecycle functions are awaited
