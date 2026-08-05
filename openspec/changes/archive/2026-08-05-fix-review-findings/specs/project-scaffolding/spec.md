# Project Scaffolding — delta

## MODIFIED Requirements

### Requirement: Names are validated before writing

Project and app names supplied by the user MUST be validated against the same identity grammar
the kernel enforces for object names, and MUST be rejected before any content is written. A
name that would escape the target directory MUST be rejected.

Escape detection MUST cover every path form the host platform resolves: relative
traversal spelled with either separator, absolute paths, and drive- or root-qualified
forms. The rejection happens in the validation step, before any filesystem operation —
not only at a final write barrier — and it applies equally to paths supplied by a
template set, so a third-party template cannot name a target outside the directory
being generated.

#### Scenario: Invalid name rejected

- **WHEN** generation is requested with a name that does not satisfy the identity grammar
- **THEN** the operation fails naming the offending value and the grammar it must satisfy, and
  nothing is written

#### Scenario: Traversal rejected

- **WHEN** a name is supplied that would resolve outside the target directory
- **THEN** the operation fails and nothing is written outside that directory

#### Scenario: Traversal with the platform's alternate separator is rejected

- **WHEN** a template entry or name spells parent-directory traversal with the host
  platform's alternate separator (for example a backslash)
- **THEN** validation rejects it before any filesystem operation, and nothing is written

#### Scenario: Drive- or root-qualified targets are rejected

- **WHEN** a template entry or name designates an absolute, drive-qualified, or
  root-qualified location
- **THEN** validation rejects it before any filesystem operation, and nothing is written
  outside the target directory
