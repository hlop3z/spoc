## MODIFIED Requirements

### Requirement: Template sets are validated before use

A template set MUST be checked for completeness before any content is written. A set that omits
an element the scaffolding operations require, or that declares a substitution value the
operation cannot supply, MUST fail naming what is missing.

A template set MUST also be checked against the destinations the generating operation reserves
for its own content. A set that declares a file landing on a reserved destination MUST fail
naming that destination, before anything is written. What a template set may declare is therefore
bounded in both directions: it MUST supply everything the operation requires, and it MUST NOT
claim anything the operation reserves.

Both checks MUST apply identically whatever the set's origin, so no set gains latitude by being
built in and none is held to a stricter standard for being retrieved.

#### Scenario: Incomplete template set

- **WHEN** an operation runs against a template set that omits a required element
- **THEN** the operation fails naming the missing element, and nothing is written

#### Scenario: Unsatisfiable substitution

- **WHEN** a template set declares a substitution value that the invoking operation does not
  supply
- **THEN** the operation fails naming that value, and nothing is written

#### Scenario: Reserved destination is refused

- **WHEN** an operation runs against a template set declaring a file whose destination is
  reserved to the generating operation
- **THEN** the operation fails naming that destination as reserved, and nothing is written

#### Scenario: Validation does not vary with origin

- **WHEN** the same defect — a missing element, an unsatisfiable value, or a claimed reserved
  destination — is present in a built-in set and in a set obtained from outside the local system
- **THEN** both fail in the same way, and neither writes anything
