# Framework Lifecycle — Delta

## ADDED Requirements

### Requirement: App-authored lifecycle failures propagate unwrapped

A failure raised by app-authored lifecycle code MUST reach the caller as the exception
the app code raised, carrying its original type and traceback. App-authored lifecycle
code means a kind's startup or shutdown hook, or a module's initialize or teardown
function. The kernel MUST NOT wrap the failure
in a kernel error or flatten it into a message string. Failures the kernel itself
authors (ordering violations, coroutine refusal, configuration errors) remain kernel
errors. Start's rollback contract is unchanged: an app-authored failure during start
still tears down what came up and returns the framework to its inert state before the
exception escapes.

#### Scenario: Module initialize raises

- **WHEN** a module's initialize function raises an application-defined error during
  start
- **THEN** start fails with that exact error type and traceback, no kernel wrapper
  appears in the exception chain above it, and the framework is returned to its inert
  state

#### Scenario: Shutdown hook raises

- **WHEN** a kind's shutdown hook raises an application-defined error during shutdown
- **THEN** shutdown fails with that exact error, not a kernel error naming it

#### Scenario: Kernel failures remain kernel errors

- **WHEN** the synchronous path encounters a coroutine hook it cannot run
- **THEN** the failure is a kernel error, exactly as the asynchronous-lifecycle
  requirement states

### Requirement: Hooks receive an ordered, immutable component collection

A kind's startup and shutdown hooks MUST receive the components of that kind belonging
to the module's app as an immutable collection in the registry's canonical enumeration
order — ordered by canonical identifier, the same order registry enumeration yields.
Two starts of the same project MUST hand every hook its components in the same order.

#### Scenario: Hook payload order is canonical identifier order

- **WHEN** an app module declares several components of a hooked kind and start runs
- **THEN** the startup hook receives exactly those components, ordered by their
  canonical identifiers

#### Scenario: Hook payload is immutable

- **WHEN** a startup hook attempts to mutate the collection it receives
- **THEN** the mutation fails, and the registry is unaffected
