## MODIFIED Requirements

### Requirement: Records carry projection-sufficient metadata

Each registry record MUST expose at minimum: the canonical identifier, the three
identifier segments individually, the registered object itself, and the metadata
supplied at registration, conforming to the contract stated by the record's kind. A record
MUST additionally admit a description of its registered object's type, so that a consumer
holding a record can be told what the object is rather than only that an object exists; a
record whose object type is not described MUST behave exactly as an undescribed record does
today, placing no constraint on the object. An external consumer MUST be able to build a
projection (routes, schemas, documentation) by reading records alone, without importing or
inspecting the kernel's internals. A record MUST NOT carry an additional free-form
configuration channel alongside its metadata: everything a projection reads about a
component beyond its identity and its object comes through the one channel its kind
describes, so a consumer can know from the declaration what a record of that kind will
contain.

#### Scenario: Projection from records only

- **WHEN** an external surface enumerates the registry through the public API
- **THEN** for every record it can obtain the identifier, kind, namespace, name, the
  object, and the registration metadata
- **AND** it needs no other kernel API to build its projection

#### Scenario: Metadata shape is knowable from the declaration

- **WHEN** an external surface reads the metadata contract a kind states, then enumerates
  records of that kind
- **THEN** every record's metadata conforms to that contract
- **AND** the surface needs no per-record inspection to learn what fields to expect

#### Scenario: No second free-form channel

- **WHEN** an external surface enumerates a record
- **THEN** it finds exactly one metadata channel on that record, described by the kind
- **AND** there is no additional untyped configuration mapping to consult

#### Scenario: An undescribed record is unconstrained

- **WHEN** a record is created without a description of its object's type
- **THEN** the record carries the object unchanged
- **AND** no constraint is placed on what the object may be

#### Scenario: A described record reports its object type

- **WHEN** a consumer holds a record whose object type has been described
- **THEN** the consumer can obtain that description alongside the record's other facets
- **AND** the record's runtime behavior is identical to an undescribed record's
