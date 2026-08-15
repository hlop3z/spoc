# Component Registry — delta

## MODIFIED Requirements

### Requirement: Enumeration is deterministic

Enumerating the registry, or any facet of it, MUST yield each matching record exactly
once, in a deterministic order for a given registered set.

Reading one facet MUST cost in proportion to that facet, not to the registry as a
whole: the time to enumerate or navigate one kind, one namespace, or one component
MUST NOT grow in proportion to how many unrelated components are registered.
Registration MAY pay the bookkeeping that makes this so, since registering is the
only operation that changes what a read can observe.

The work of putting records into their deterministic order MUST be paid at most once
per change to the registered set, not once per read: enumerating an unchanged registry
repeatedly MUST NOT re-derive the ordering each time. A registration between reads MAY
cause the next read to pay the derivation again.

#### Scenario: Stable enumeration

- **WHEN** the registry is enumerated twice without intervening registrations
- **THEN** both enumerations yield the same records in the same order

#### Scenario: Reading one facet does not pay for the rest

- **WHEN** a registry holds many components and one facet of it is read — one kind's
  records, one namespace's names, or one component by its segments
- **THEN** the read's cost tracks the size of that facet, and registering many further
  components in *other* facets does not proportionally slow it

#### Scenario: Repeated enumeration does not re-derive order

- **WHEN** the registry is enumerated many times without intervening registrations
- **THEN** the ordering derivation is performed at most once across those reads, and
  every read still yields the same records in the same order

#### Scenario: A registration between reads is observed

- **WHEN** the registry is enumerated, a further component is registered, and the
  registry is enumerated again
- **THEN** the second enumeration includes the new component in its deterministic
  position, exactly as if no read had preceded the registration
