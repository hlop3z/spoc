## ADDED Requirements

### Requirement: A namespace MUST belong to exactly one package

A namespace MUST be owned by exactly one package for the lifetime of a running project.
Whatever rule derives a namespace, two distinct packages resolving to the same namespace
MUST be refused rather than merged, because the grammar's promise that an identifier names
one thing cannot hold when one namespace names two places. The refusal MUST name the
contested namespace and both claiming packages, so the author can see the collision without
inspecting the layout.

Ownership MUST be decided before any component of a contested namespace is registered, so
the failure is reported once, in terms of the declaration, rather than surfacing later as a
name collision between two objects that appear unrelated.

#### Scenario: Two packages claiming one namespace

- **WHEN** two distinct packages are installed and both resolve to the namespace `shop`
- **THEN** start fails with an error naming `shop` and both claiming package paths

#### Scenario: One package claiming its own namespace repeatedly

- **WHEN** the same package is the source of several registrations in one namespace
- **THEN** every registration succeeds, because the namespace has one owner

#### Scenario: Ownership is settled before registration

- **WHEN** two packages contest a namespace and neither declares an object name the other
  declares
- **THEN** start still fails naming the contested namespace
- **AND** the failure does not depend on any object name coinciding
