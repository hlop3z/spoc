# Component Registry

## Purpose

One flat, enumerable store of component records is the kernel's single source
of truth. External surfaces build every projection (routes, schemas, docs) by
reading records through the public API; grouped views are derived, and no
declared component is ever silently dropped.

## Requirements

### Requirement: Single flat store

All registered components MUST live in one registry: a single enumerable collection of
component records. Kind, namespace, and name MUST be queryable facets of that one
collection, not separate stores. Any grouped view (e.g. "all components of kind
`model`") MUST be derived from the registry, never maintained as independent state.

#### Scenario: One registry, many facets

- **WHEN** a component `model:blog.post` is registered
- **THEN** it is present in the full enumeration, in the kind-`model` facet, and in the
  namespace-`blog` facet, and all three views expose the same record

### Requirement: Registration is loud

Discovery and registration MUST NOT silently drop a declared component. If an object is
declared as a component but cannot be registered — its kind does not match its declared
location, its identifier is invalid, or its kind is unknown — startup MUST fail with an
error naming the object, its declared location, and the reason.

#### Scenario: Kind and location mismatch fails startup

- **WHEN** an object declared as kind `model` is discovered in the location reserved for
  kind `view`
- **THEN** startup fails with an error naming the object, both kinds, and the location
- **AND** the component is not silently omitted from the registry

#### Scenario: Duplicate identifier rejected

- **WHEN** two objects are registered under the same canonical identifier
- **THEN** the second registration fails with an error naming the identifier and the
  already-registered object

### Requirement: Records carry projection-sufficient metadata

Each registry record MUST expose at minimum: the canonical identifier, the three
identifier segments individually, the registered object itself, and the metadata
supplied at registration, conforming to the contract stated by the record's kind. An
external consumer MUST be able to build a projection (routes, schemas, documentation) by
reading records alone, without importing or inspecting the kernel's internals. A record
MUST NOT carry an additional free-form configuration channel alongside its metadata:
everything a projection reads about a component beyond its identity and its object comes
through the one channel its kind describes, so a consumer can know from the declaration
what a record of that kind will contain.

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

### Requirement: Enumeration is deterministic

Enumerating the registry, or any facet of it, MUST yield each matching record exactly
once, in a deterministic order for a given registered set.

#### Scenario: Stable enumeration

- **WHEN** the registry is enumerated twice without intervening registrations
- **THEN** both enumerations yield the same records in the same order
