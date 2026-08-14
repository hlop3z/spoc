# Delta: component-registry

## MODIFIED Requirements

### Requirement: Single flat store

All registered components MUST live in one registry: a single enumerable collection of
component records. Kind, namespace, and name MUST be queryable facets of that one
collection, not separate stores. Any grouped view (e.g. "all components of kind
`model`") MUST be derived from the registry, never maintained as independent state.

Where the registry keeps state that is not a view of that collection and so cannot be
derived from it, every write to it MUST happen in the same atomic step that admits a
registration, and the set of such state MUST be enumerable rather than discovered by
reading every method.

#### Scenario: One registry, many facets

- **WHEN** a component `model:blog.post` is registered
- **THEN** it is present in the full enumeration, in the kind-`model` facet, and in the
  namespace-`blog` facet, and all three views expose the same record

#### Scenario: No view can be seen without the others

- **WHEN** a registration completes and any facet or the full enumeration is read,
  including concurrently with other registrations
- **THEN** every view that should contain the new record contains it, and none reports a
  record the others do not — a partially admitted registration is never observable

### Requirement: Enumeration is deterministic

Enumerating the registry, or any facet of it, MUST yield each matching record exactly
once, in a deterministic order for a given registered set.

Reading one facet MUST cost in proportion to that facet, not to the registry as a
whole: the time to enumerate or navigate one kind, one namespace, or one component
MUST NOT grow in proportion to how many unrelated components are registered.
Registration MAY pay the bookkeeping that makes this so, since registering is the
only operation that changes what a read can observe.

#### Scenario: Stable enumeration

- **WHEN** the registry is enumerated twice without intervening registrations
- **THEN** both enumerations yield the same records in the same order

#### Scenario: Reading one facet does not pay for the rest

- **WHEN** a registry holds many components and one facet of it is read — one kind's
  records, one namespace's names, or one component by its segments
- **THEN** the read's cost tracks the size of that facet, and registering many further
  components in *other* facets does not proportionally slow it
