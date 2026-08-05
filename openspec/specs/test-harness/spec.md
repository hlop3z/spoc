# Test Harness

## Purpose

The distribution ships the machinery a downstream project needs to test an
application built on the kernel: isolated framework construction with
guaranteed teardown, declarative app-tree building, and mode override. The
harness consumes only the kernel's public contracts, works without any test
runner, and the kernel never imports it.

## Requirements

### Requirement: Isolated framework construction with guaranteed teardown
The test harness MUST provide an isolation scope that yields a freshly
constructed framework bound to a given project tree and, on exit — normal or
exceptional — MUST shut the framework down and restore every piece of process
state the boot mutated (module import state and import search paths), so that
two consecutive scopes observe no state from each other.

#### Scenario: State restored after normal exit
- **WHEN** an isolation scope boots a framework against a project tree and the scope exits normally
- **THEN** the framework is shut down, and module import state and import search paths match their pre-scope values

#### Scenario: State restored after an exception
- **WHEN** the body of an isolation scope raises an exception
- **THEN** teardown still runs in full and the exception propagates unchanged

#### Scenario: Consecutive scopes are independent
- **WHEN** one isolation scope registers objects and exits, and a second scope boots against a different project tree
- **THEN** the second scope's registry contains no records from the first

### Requirement: Harness usable without any test runner
The harness MUST be importable and fully functional with no test runner
present or installed; it MUST depend only on the language's standard library
and the kernel's public contracts.

#### Scenario: Plain-script usage
- **WHEN** a plain script (no test runner) imports the harness and uses an isolation scope
- **THEN** construction, boot, resolution, and teardown all work as specified

### Requirement: Containment from the kernel
Importing the root package or any kernel module MUST NOT import the test
harness; the harness is a consumer of the kernel's public contracts only.

#### Scenario: Kernel never loads the harness
- **WHEN** the root package is imported and a framework is booted
- **THEN** the test-harness subpackage is absent from loaded modules

### Requirement: Declarative app-tree builder
The harness MUST provide a builder that materializes a bootable project tree
from a declarative description — apps, their modules with source content, and
project configuration — without requiring the caller to know the on-disk
layout conventions.

#### Scenario: Built tree boots
- **WHEN** a caller declares one app containing one module that registers one object, builds the tree, and boots a framework against it
- **THEN** the object resolves by its canonical identifier

#### Scenario: Multiple apps with configuration
- **WHEN** a caller declares several apps and project configuration entries (mode, per-mode app lists)
- **THEN** the built tree's configuration reflects the declaration and boot honors it

### Requirement: Mode override scope
The harness MUST provide a scope that runs its body under a stated mode and,
on exit, MUST restore the prior configuration, so that mode-dependent behavior
can be exercised without permanently altering the project tree or process
state.

#### Scenario: Override applies and reverts
- **WHEN** a project configured for one mode is exercised inside a mode-override scope stating a different mode
- **THEN** within the scope the framework reports the overridden mode and loads that mode's app list, and after exit the original configuration is observed again
