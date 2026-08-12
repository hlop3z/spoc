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

### Requirement: Load order is a stated total order

The framework MUST load and initialize app modules in a total order determined by exactly
two things, in this precedence: the depth of a module's kind in the declared inter-kind
dependency order, and the position of the module's app in the effective installed-app list.
Kind depth decides first; the app list breaks every remaining tie. Two starts of the same
project MUST produce the same order, and the order MUST NOT depend on filesystem layout,
dictionary iteration, or the order in which modules happen to import one another.

A kind's depth MUST be read from the declaration, never from which modules were found. An
app that omits an optional kind therefore changes the position of no module but its own:
the omission MUST NOT move that app's remaining modules into an earlier phase, and MUST NOT
reorder any other app.

Because kind depth is the first key, the modules of one kind form a load phase that
completes across every installed app before the next phase begins. Because the installed-app
list is the tiebreak, an author who needs one app's modules of a kind to load before
another's states that by ordering the app list, and no other declaration is required.

The order MUST be a property the framework states rather than one inherited from a
third-party ordering utility, so that a change of implementation cannot silently weaken it.

#### Scenario: Kind depth decides before app position

- **WHEN** apps `blog` and `shop` are installed in that order, and kind `views` depends on
  kind `models`
- **THEN** the load order is `blog.models`, `shop.models`, `blog.views`, `shop.views`

#### Scenario: App list order breaks the tie within a phase

- **WHEN** the same two apps are installed in the order `shop`, `blog`
- **THEN** `shop.models` is loaded and initialized before `blog.models`
- **AND** both are still loaded and initialized before either app's `views` module

#### Scenario: The order is stable across starts

- **WHEN** the same project is started twice in one process, with a shutdown between
- **THEN** both starts load and initialize modules in the same order

#### Scenario: An omitted optional kind moves nothing else

- **WHEN** kinds `models`, `views`, and `urls` each depend on the previous one, `views` is
  optional, apps `blog` and `shop` are installed in that order, and `shop` has no `views`
  module
- **THEN** the order is `blog.models`, `shop.models`, `blog.views`, `blog.urls`, `shop.urls`
- **AND** `shop.urls` is loaded and initialized after every app's `views` module, exactly as
  it would be if `shop` had one

#### Scenario: A cycle in the declared kind order is refused

- **WHEN** the declared kinds contain a dependency cycle
- **THEN** start fails naming the cycle, and no ordering is produced

### Requirement: Lifecycle hooks fire in load order

The framework MUST fire each kind's startup hook, and each module's own initialization, in
the load order stated above, and MUST fire the paired shutdown work in the exact reverse.
Hook firing is the surface through which load order is observable, so the two MUST NOT be
allowed to diverge: a startup hook for a dependent kind MUST NOT run before the startup
hook of a depended-on kind has run for every installed app.

#### Scenario: A dependent kind's hook sees every app's contribution

- **WHEN** kind `views` depends on kind `models`, two apps are installed, and both kinds
  declare startup hooks
- **THEN** the `models` startup hook has run for both apps before the `views` startup hook
  runs for either

#### Scenario: Teardown reverses the load order exactly

- **WHEN** a started framework with two apps and two dependent kinds is shut down
- **THEN** shutdown work runs in the exact reverse of the order in which startup work ran

### Requirement: No declaration may invert the phase order

The framework MUST NOT provide any way to declare that a module of a deeper kind loads
before a module of a shallower kind, in the same app or across apps. Ordering between apps
is expressible only within one kind phase. A declaration form whose meaning would place a
whole app ahead of another app's earlier-phase modules MUST be refused, because the phase
guarantee cannot survive it.

#### Scenario: Ordering between apps stays inside a phase

- **WHEN** any supported declaration orders one app against another
- **THEN** that ordering affects only the relative position of their modules within each
  kind phase
- **AND** it never moves a module of one kind ahead of any module of a kind it depends on

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

Hook dispatch is per loaded module: a kind's hooks fire once for each loaded app
module of that kind, receiving the components that app contributed. Components
registered without a backing app module — configured registrations — do not, by
themselves, cause hooks to fire, and this dispatch rule MUST be stated in the lifecycle
documentation rather than left for the author to discover from a hook that never ran.

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

### Requirement: Hook pairing is symmetric under a failed boot

When a boot fails partway, every module whose kind startup hook has fired MUST have its
kind shutdown hook fired during rollback, whether or not that module's own initialize
completed. Rollback MUST never leave a fired startup hook without its paired shutdown
hook.

#### Scenario: Initialize failure still pairs the hooks

- **WHEN** a module's initialize raises after its kind's startup hook has fired
- **THEN** rollback fires that kind's shutdown hook for that module before start's
  failure escapes, and the framework returns to its inert state

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
