# Framework Lifecycle

## Purpose

The framework has an explicit phase contract: inert after construction, loud
discovery on an explicit start, a single post-discovery ready phase for
cross-component work, and ordered shutdown. Nothing happens as a side effect
of import, and every phase fails loudly rather than half-completing.

## Requirements

### Requirement: Construction is inert

Constructing a framework object MUST have no observable side effects: no filesystem
reads or writes, no process-global mutation, and no application-module loading.
Construction only records the declaration.

#### Scenario: Construct without a project

- **WHEN** a framework object is constructed in an environment with no project files
  at all
- **THEN** construction succeeds and nothing outside the object changes

### Requirement: Explicit start boots the framework

The framework MUST perform all discovery (locating the project, reading
configuration, loading app modules in dependency order, and collecting marked
components into the registry) in one explicit start step that takes the project root.
Discovery failures follow the component-registry capability: loud, naming the object
and reason. Starting an already-started framework MUST fail rather than silently
re-discover.

#### Scenario: Start performs discovery

- **WHEN** start is invoked with a project root containing configured apps
- **THEN** app modules load in dependency order and every marked component is present
  in the registry when start returns

#### Scenario: Double start

- **WHEN** start is invoked on a framework that has already started
- **THEN** the call fails, stating the framework is already started

### Requirement: A missing module resolves against its own kind's optionality

When a declared app does not provide a module for a declared kind, the framework MUST
decide whether that is an error by consulting the optionality stated on that kind alone.
A missing module for a required kind MUST fail start, naming the app, the kind, and the
module that was expected. A missing module for an optional kind MUST be skipped without
error and without appearing in the registry. No framework-wide setting SHALL override
this per-kind decision, so tolerating one absent kind never silently tolerates another.

#### Scenario: Missing module for a required kind

- **WHEN** an app declared in configuration provides no module for a required kind
- **THEN** start fails, naming the app, the kind, and the expected module

#### Scenario: Missing module for an optional kind

- **WHEN** an app declared in configuration provides no module for an optional kind
- **THEN** start proceeds, that app contributes no components of that kind, and no error
  is raised

#### Scenario: Optionality does not leak between kinds

- **WHEN** a framework declares one optional kind and one required kind, and an app
  provides a module for neither
- **THEN** start fails on the required kind alone, and the absent optional kind is not
  reported as an error

#### Scenario: A module that exists but fails to load is always an error

- **WHEN** an app provides a module for an optional kind and loading that module raises
- **THEN** start fails with that error, because the module was present and broken rather
  than absent

### Requirement: Ready phase after discovery

The framework MUST offer a ready phase: callbacks registered before start that fire
exactly once, after all components are registered and before start returns, receiving
read access to the completed registry. Callbacks fire in registration order. A ready
callback failure fails start.

#### Scenario: Cross-component finalization

- **WHEN** a ready callback enumerates the registry to build derived structures
- **THEN** it observes every registered component of every kind, exactly once per
  start

#### Scenario: Ready failure is a start failure

- **WHEN** a ready callback raises an error
- **THEN** start fails with that error and the framework is not reported as started

### Requirement: Ordered shutdown

Shutdown MUST tear down initialized modules in reverse dependency order and fire
shutdown hooks before each module's teardown. Shutting down a framework that never
started MUST be a harmless no-op.

#### Scenario: Reverse-order teardown

- **WHEN** shutdown is invoked after a successful start where `views` depends on
  `models`
- **THEN** `views` modules are torn down before `models` modules

#### Scenario: Shutdown without start

- **WHEN** shutdown is invoked on a framework that was never started
- **THEN** the call returns without error and without side effects

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

### Requirement: Boot acquires no process-global state

Start MUST NOT mutate the interpreter's module search path, MUST NOT create,
modify, or delete any file or directory, and MUST NOT make any package
importable under a name it does not already have. App modules are imported
through the language's normal import mechanism under their declared dotted
paths. The only process-global state a boot may leave behind is the language
runtime's own module cache, populated by those ordinary imports.

#### Scenario: No import-path mutation

- **WHEN** start runs and loads configured apps
- **THEN** the interpreter's module search path is identical before and after
  start, and a module whose name collides with an app's final path segment
  (for example a standard-library module) still resolves to what it resolved
  to before start

#### Scenario: No filesystem side effects

- **WHEN** start is invoked with a project root that contains no apps
  directory
- **THEN** no directory is created, and the filesystem under the project root
  is byte-identical before and after the call

### Requirement: Lifecycle transitions are serialized

Concurrent invocations of start and shutdown MUST be serialized against each
other and against themselves. When multiple callers race to start the same
framework, exactly one start proceeds; every other caller fails with the
already-started error. A shutdown racing a start MUST observe either the
fully-started or the fully-inert state, never a partial boot.

#### Scenario: Racing starts

- **WHEN** two threads invoke start on the same framework concurrently
- **THEN** exactly one start succeeds, the other fails stating the framework
  is already started, and every discovered component is present in the
  registry exactly once

### Requirement: Asynchronous lifecycle path

The framework MUST offer an asynchronous start and an asynchronous shutdown
whose observable behavior equals the synchronous ones. Kind lifecycle hooks
and module initialize/teardown functions declared as coroutine functions MUST
be awaited by the asynchronous path. The synchronous path MUST fail loudly,
naming the offending hook or module, when it encounters a coroutine it cannot
run — it never skips one and never half-runs it.

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

### Requirement: App-authored lifecycle failures propagate unwrapped

A failure raised by app-authored lifecycle code MUST reach the caller as the exception
the app code raised, carrying its original type and traceback. App-authored lifecycle
code means a kind's startup or shutdown hook, or a module's initialize or teardown
function. The kernel MUST NOT wrap the failure in a kernel error or flatten it into a
message string. Failures the kernel itself
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

### Requirement: Restart rebuilds kernel state, not module state

After shutdown the framework MUST reset everything the kernel owns (the
registry, module-ordering bookkeeping, and loaded configuration), and a
subsequent start MUST rebuild the registry by re-running discovery. The
contract MUST state that the language runtime's module cache and any
module-level state persist across restarts: module-level code executes at
most once per process, and the kernel makes no claim of reloading it.

#### Scenario: Restart re-registers from cached modules

- **WHEN** a framework starts, shuts down, and starts again in one process
- **THEN** the second start succeeds, the registry again contains every
  discovered component, and module-level side effects (such as an import-time
  counter) have occurred exactly once
