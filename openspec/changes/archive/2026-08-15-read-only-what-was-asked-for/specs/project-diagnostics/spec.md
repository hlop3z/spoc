# Project Diagnostics

## MODIFIED Requirements

### Requirement: Registry enumeration
The system MUST provide a list operation that boots the project's
declaration, enumerates every registered record's canonical identifier —
optionally narrowed by kind or namespace facet — and tears the boot down
completely before returning.

A narrowing by kind MUST be answered by reading that kind's facet, not by enumerating
every registered record and discarding those that do not match. The cost of a narrowed
listing is therefore set by the facet asked for rather than by everything registered,
which is the guarantee the registry already makes to every other reader of a facet.

Ordering MUST be taken from the read that produced the records rather than re-established
by the listing operation. The registry enumerates in canonical identifier order, and a
second claim to that same order is one that could later disagree with the first.

#### Scenario: All identifiers listed
- **WHEN** the list operation runs against a valid project
- **THEN** every registered component's canonical identifier is reported, in deterministic order

#### Scenario: Facet narrowing
- **WHEN** the list operation is narrowed to one kind
- **THEN** only that kind's identifiers are reported, and an unknown kind fails naming the valid kinds

#### Scenario: Narrowing costs the facet
- **WHEN** the list operation is narrowed to one kind in a registry holding many kinds
- **THEN** the records of other kinds are not enumerated, and the reported order is the
  canonical identifier order the facet read already carries

#### Scenario: Namespace narrowing stays an open set
- **WHEN** the list operation is narrowed to a namespace that holds no records
- **THEN** the result is empty rather than a failure, because namespaces are an open set
