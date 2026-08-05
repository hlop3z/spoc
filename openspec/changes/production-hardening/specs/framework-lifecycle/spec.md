# Framework Lifecycle — Delta

## ADDED Requirements

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
