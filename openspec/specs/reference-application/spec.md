# Reference Application

## Purpose

The repository carries one runnable reference project — a coherent domain
built on the kernel's public contracts — and the test suite boots it, so
the worked example can never silently drift from the kernel. It is both the
evaluator's answer to "what does a real SPOC project look like" and the
project's own friction-finding instrument.

## Requirements

### Requirement: One runnable reference project
The repository MUST carry one reference project that runs unedited and
demonstrates, in a coherent domain, every public kernel contract a
downstream project composes: several apps installed across modes, an object
in one namespace resolved from another at runtime through the registry,
plugin-configured registrations, and a surface projected purely by
enumerating the registry.

#### Scenario: Reference project boots and registers the domain
- **WHEN** the reference project is started through the public API
- **THEN** the registry contains the domain's components across several namespaces, exactly as declared

#### Scenario: Cross-namespace resolution at runtime
- **WHEN** a component in one app resolves a component of another app while handling a call
- **THEN** the resolution goes through the registry's public API and returns the other namespace's registered object

#### Scenario: Projected surface derives from the registry alone
- **WHEN** the reference project's HTTP surface is constructed
- **THEN** every route corresponds to a registry record, with no route defined anywhere else

### Requirement: Both lifecycles are demonstrated
The reference project MUST include a synchronous entry point and an
asynchronous entry point whose declaration carries coroutine hooks; each
boots, serves its purpose, and shuts down through its own path.

#### Scenario: Synchronous entry
- **WHEN** the synchronous entry point runs
- **THEN** the project boots, enumerates its registry, and shuts down on the synchronous path

#### Scenario: Asynchronous entry
- **WHEN** the asynchronous entry point runs
- **THEN** coroutine hooks are awaited around boot and shutdown on the asynchronous path

### Requirement: The suite pins the reference project
The test suite MUST boot the reference project and exercise its declared
behaviors, so that a kernel change that breaks the worked example fails the
same gate as any other regression; continuous integration MUST run these
tests with the projection's dependencies present, not skipped.

#### Scenario: Drift fails the suite
- **WHEN** a kernel change breaks the reference project's boot, resolution, or projection
- **THEN** the standard test gate fails, naming the broken expectation

#### Scenario: The projection is genuinely constructed in CI
- **WHEN** the suite runs in continuous integration
- **THEN** the HTTP projection test constructs the real application object rather than being skipped for a missing dependency
