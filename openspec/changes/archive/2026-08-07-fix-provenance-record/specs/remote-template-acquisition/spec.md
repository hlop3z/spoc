## MODIFIED Requirements

### Requirement: Retrieval completes before anything is written

A remote template set MUST be fully retrieved, admitted, and validated before any file is
written to the destination. Failure to retrieve, failure to admit any part of the retrieved
content, or failure to validate the resulting template set MUST leave the destination
untouched.

A failure MUST name the reference in the form the caller supplied it. A location the operation
derived from that reference MAY additionally be reported as detail, but MUST NOT stand in place
of the reference: the caller can only correct what they wrote, and a derived location names
something they never typed.

#### Scenario: Retrieval failure writes nothing

- **WHEN** a remote reference cannot be retrieved
- **THEN** the operation fails naming the reference and the reason, and no file is created or
  modified at the destination

#### Scenario: Failure names what the caller supplied

- **WHEN** retrieval of a remote reference fails at a location the operation derived from that
  reference
- **THEN** the failure names the reference as the caller supplied it, and does not report the
  derived location alone

#### Scenario: Retrieved set is validated like any other

- **WHEN** a retrieved template set omits a required element or declares an unsatisfiable
  substitution value
- **THEN** the operation fails identically to the same defect in a local template set, and
  writes nothing
