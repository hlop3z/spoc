# Pytest Integration

## Purpose

The harness's pieces are surfaced as test-runner fixtures through the
runner's standard plugin discovery, shipped in the one distribution without
making the runner a runtime dependency.

## Requirements

### Requirement: Harness surfaced as test-runner fixtures
The distribution MUST expose the test harness's isolation scope, app-tree
builder, and mode-override scope as fixtures through the test runner's
standard plugin discovery mechanism, so that a downstream project gets them
by installing the one distribution alongside its test runner — no extra
package, no manual registration.

#### Scenario: Fixtures available after install
- **WHEN** a downstream project has the distribution and the test runner installed and runs its suite
- **THEN** the harness fixtures are resolvable by name in its tests without any configuration

#### Scenario: Fixture teardown on test failure
- **WHEN** a test using the isolation fixture fails
- **THEN** the harness teardown still runs in full and subsequent tests observe no leaked state

### Requirement: Plugin is inert without the test runner
The plugin MUST live in the one distribution without making the test runner a
runtime dependency: installing and importing the distribution in an
environment without the test runner MUST succeed and load nothing from the
plugin.

#### Scenario: Runtime environment unaffected
- **WHEN** the distribution is installed in an environment without the test runner and the root package is imported
- **THEN** the import succeeds and no plugin or test-runner module is loaded
