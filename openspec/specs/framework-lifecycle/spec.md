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
