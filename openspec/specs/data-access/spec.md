# Data Access

## Purpose

Two ways to reach into the intermediate representation, kept separate because their
failure semantics differ: exact addressing (RFC 6901, JSON Pointer) resolves one value or
fails, for locations whose absence is a defect; querying (RFC 9535, JSONPath) returns a
result set that may legitimately be empty, for selections whose emptiness is an answer.
Neither may be relaxed into the other. Both behave identically regardless of which format
the representation was read from.

## Requirements

### Requirement: Exact addressing resolves one value or fails loudly

Addressing a single value within the intermediate representation MUST use the adopted exact
addressing standard for JSON documents (RFC 6901, JSON Pointer). An exact address MUST resolve
to exactly one value, or fail.

A failure MUST name the portion of the address that could not be resolved, rather than
reporting a blanket absence. An address that resolves to no value MUST NOT be reported as an
empty result, a null, or a default.

An address that is not syntactically valid under the adopted standard MUST fail through
the surface's own declared error family, naming the address — never as an error type
belonging to an underlying implementation.

#### Scenario: A valid address resolves to its value

- **WHEN** an exact address naming an existing location is applied to a representation
- **THEN** exactly that one value is returned

#### Scenario: A misspelled address fails rather than reading as absent

- **WHEN** an exact address is applied whose intermediate segment does not exist
- **THEN** the operation fails identifying the segment that could not be resolved, and does not
  return a null, an empty result, or a default

#### Scenario: Absent and null are distinguishable

- **WHEN** an exact address resolves to a location whose stored value is null, and separately an
  exact address names a location that does not exist
- **THEN** the first returns the null value and the second fails, and the two outcomes are
  distinguishable by the caller

#### Scenario: Array positions are addressable

- **WHEN** an exact address names a position within an array
- **THEN** that element is returned, and an out-of-range position fails naming the position

#### Scenario: A malformed address fails within the declared error family

- **WHEN** a syntactically invalid exact address is applied
- **THEN** the operation fails with the surface's own error family naming the address,
  and no underlying implementation's error type reaches the caller

### Requirement: Querying returns a possibly-empty result set

Querying the intermediate representation MUST use the adopted query standard for JSON documents
(RFC 9535, JSONPath). A query MUST return a result set that may legitimately be empty, and an
empty result MUST NOT be an error.

The implementation MUST conform to that standard specifically, verified against its published
compliance test suite, rather than to any pre-standard dialect.

A query that is not syntactically valid under the adopted standard MUST fail through the
surface's own declared error family, naming the query — never as an error type belonging
to an underlying implementation. Where the surface narrows an implementation to the
standard by disabling non-standard syntax, that narrowing MUST be pinned by verification,
so a change in the underlying implementation cannot silently widen the accepted syntax.

#### Scenario: A matching query returns its matches

- **WHEN** a query matching several locations is applied
- **THEN** all matching values are returned, in the order the standard defines

#### Scenario: A non-matching query returns empty, not an error

- **WHEN** a query matching no location is applied
- **THEN** an empty result set is returned and no failure is raised

#### Scenario: Filtering selects records from tabular data

- **WHEN** a filter query is applied to a representation read from a tabular source
- **THEN** exactly the records satisfying the filter are returned

#### Scenario: Conformance is verified, not asserted

- **WHEN** the query surface is validated
- **THEN** it is checked against the published compliance test suite for the adopted standard,
  and any unsupported portion of the standard is stated explicitly

#### Scenario: A malformed query fails within the declared error family

- **WHEN** a syntactically invalid query is applied
- **THEN** the operation fails with the surface's own error family naming the query, and
  no underlying implementation's error type reaches the caller

#### Scenario: Narrowing to the standard is drift-guarded

- **WHEN** the underlying query implementation changes such that syntax outside the
  adopted standard would become accepted
- **THEN** verification fails, rather than the non-standard syntax becoming silently
  available

### Requirement: The two addressing modes are distinguished by failure semantics

Exact addressing and querying MUST be separate operations with separate result contracts, and
the distinction MUST be stated where a caller chooses between them: exact addressing is for
values whose absence is a defect, querying is for selections whose emptiness is an answer.

Neither operation may substitute for the other by relaxing its failure contract — querying MUST
NOT raise on no match, and exact addressing MUST NOT return an empty result on no match.

#### Scenario: The same missing location behaves differently by mode

- **WHEN** the same absent location is requested once by exact address and once by query
- **THEN** the exact address fails and the query returns an empty result set

#### Scenario: Contracts are not configurable into each other

- **WHEN** either operation is invoked
- **THEN** its failure contract holds as specified, with no option that converts a query into a
  raising operation or an exact address into a silent one

### Requirement: Addressing applies uniformly across all source formats

Both addressing modes MUST behave identically regardless of which format the representation was
read from, requiring no format-specific address syntax or per-format adaptation.

#### Scenario: One address works across formats

- **WHEN** equivalent content is read from two different supported formats and the same exact
  address is applied to both
- **THEN** both return equal values

#### Scenario: One query works across formats

- **WHEN** equivalent content is read from two different supported formats and the same query is
  applied to both
- **THEN** both return equal result sets

#### Scenario: Collected entries are addressable the same way

- **WHEN** an entry obtained from a collection is addressed
- **THEN** both modes behave exactly as they do for a value read from a single source
