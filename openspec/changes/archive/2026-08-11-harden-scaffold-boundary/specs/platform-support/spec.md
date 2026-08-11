## ADDED Requirements

### Requirement: Supported platforms are declared in one place

The project MUST declare the set of platforms on which its behavior is guaranteed. That
declaration MUST be the single source the validation gate and its consumers derive from, so a
platform cannot be guaranteed without being gated, and cannot be gated without being declared.

A platform absent from the declaration is not a supported platform, and the project MUST NOT
claim behavior on it.

#### Scenario: Declaration and gate agree

- **WHEN** the declared set of supported platforms is compared with the set the validation gate
  executes on
- **THEN** the two sets are identical

#### Scenario: Documentation does not exceed the declaration

- **WHEN** documentation states the platforms the project runs on
- **THEN** it names no platform outside the declared set

### Requirement: The validation gate is executed on every declared platform

Admitting a change MUST require the validation gate to have passed on every declared platform.
Evidence from a proper subset of the declared platforms MUST NOT be sufficient, regardless of
which subset it is.

Where a check is inherently platform-independent, executing it on one platform MAY satisfy it,
provided the checks whose outcome can differ by platform are executed on each.

#### Scenario: A platform-specific failure blocks admission

- **WHEN** the gate passes on one declared platform and fails on another
- **THEN** the change is not admitted

#### Scenario: A missing leg is not a pass

- **WHEN** the gate does not execute on a declared platform
- **THEN** that platform's result is reported as absent rather than assumed to pass

### Requirement: Platform-conditional behavior is verifiable from any host

Behavior that the system selects by platform MUST be verifiable without executing on that
platform. Every platform-conditional branch MUST be reachable in a single run of the suite on
any one declared platform.

This is what keeps a contributor working on one platform from being blind to the others, and
what stops a coverage measurement from depending on the host that produced it.

#### Scenario: Every branch is exercised from one host

- **WHEN** the suite is run on any single declared platform
- **THEN** each platform-conditional branch is exercised, including those the host would never
  select for itself

#### Scenario: Measured coverage does not depend on the host

- **WHEN** the suite is run on two different declared platforms
- **THEN** the set of exercised platform-conditional branches is the same in both runs
