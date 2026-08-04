# Component Registry

## ADDED Requirements

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
identifier segments individually, the registered object itself, and the configuration
and metadata supplied at registration. An external consumer MUST be able to build a
projection (routes, schemas, documentation) by reading records alone, without importing
or inspecting the kernel's internals.

#### Scenario: Projection from records only

- **WHEN** an external surface enumerates the registry through the public API
- **THEN** for every record it can obtain the identifier, kind, namespace, name, the
  object, and the registration metadata
- **AND** it needs no other kernel API to build its projection

### Requirement: Enumeration is deterministic

Enumerating the registry, or any facet of it, MUST yield each matching record exactly
once, in a deterministic order for a given registered set.

#### Scenario: Stable enumeration

- **WHEN** the registry is enumerated twice without intervening registrations
- **THEN** both enumerations yield the same records in the same order
