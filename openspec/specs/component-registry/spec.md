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

### Requirement: One object, one identity — divergence is loud

An object already present in the registry MUST be re-registerable only under
its existing identity: such a registration succeeds idempotently and returns
the existing record. Registering an already-registered object under a
different identity MUST fail with an error naming both the existing and the
requested identifier. The registry never silently answers a registration with
a record whose identity differs from what the caller stated.

Divergence detection tracks objects whose identity is meaningful. Registering
equal immutable values under different identifiers MUST succeed even where the
language runtime shares one underlying object for both (interning or caching);
value sharing performed by the runtime is never reported as identity
divergence.

Discovery follows the same loudness rule, but only where a second *claim* is
actually being made. A registered object appearing in a location that declares
a different kind was imported to be used, not declared again, and MUST be
skipped silently. Where two locations of the *same* kind both hold a registered
object and the identity derived at the second differs from the recorded one,
start MUST fail naming both identities — the first location MUST NOT silently
win on load order. Objects that carry their defining location intrinsically
(classes and functions) remain silently skippable wherever they are
re-exported, as their ownership is never ambiguous.

#### Scenario: Idempotent re-registration

- **WHEN** an object registered as `models:blog.post` is registered again as
  `models:blog.post`
- **THEN** the call succeeds and returns the existing record, and the registry
  still contains exactly one record for that object

#### Scenario: Divergent re-registration fails

- **WHEN** an object registered as `models:blog.post` is registered again as
  `models:shop.post`
- **THEN** the registration fails with an error naming both `models:blog.post`
  and `models:shop.post`, and the registry is unchanged

#### Scenario: Runtime value-sharing is not divergence

- **WHEN** two configured references resolve to equal immutable values that the
  runtime represents as one shared object, and each registers under its own
  identifier
- **THEN** both registrations succeed, and each identifier resolves to its own
  record

#### Scenario: Two same-kind locations claiming one instance is a loud failure

- **WHEN** a marked instance declared in one app's location for a kind is also
  present in another app's location for that same kind, so the identity derived
  at the second differs from the first
- **THEN** start fails with an error naming both identities, rather than the
  namespace being decided by which app loaded first

#### Scenario: Importing a registered object for use is not a claim

- **WHEN** a registered object is imported into a location that declares a
  different kind, so that the location can use it
- **THEN** discovery skips it silently, and it keeps the one identity it was
  registered under

### Requirement: Registration is safe under concurrency

Concurrent registrations MUST each be atomic: every accepted registration is
fully visible, no accepted registration is lost, and the duplicate-identifier
and identity-divergence guarantees hold under any interleaving. Enumeration
and resolution running concurrently with registration MUST observe only
complete records — never a partially constructed one.

A resolution that fails MUST describe one consistent observation of the registry rather
than several stitched together. The candidates a failure names, and the judgement about
which segment could not be matched, MUST come from the same observation that failed to find
the identifier — so a failure never names a candidate that did not exist when the lookup
ran, and never reports a segment as unknown that the same observation contains.

This obligation binds the failure path only. Successful resolution MUST remain a single
lookup, and the guarantee MUST NOT be met by holding exclusive access across
app-authored code or across the composition of the message.

#### Scenario: Parallel registration loses nothing

- **WHEN** many threads concurrently register distinct components
- **THEN** after all complete, every component is present in the registry
  exactly once

#### Scenario: Racing duplicates resolve to one winner

- **WHEN** two threads concurrently register different objects under the same
  identifier
- **THEN** exactly one registration succeeds and the other fails with the
  duplicate-identifier error naming the identifier and the winning object

#### Scenario: A failure describes one observation of the registry

- **WHEN** a resolution fails for an identifier whose segments do not match while other
  threads are concurrently registering components
- **THEN** the failure names only candidates drawn from the observation in which the
  lookup failed, and never contradicts that observation about which segment was unknown

#### Scenario: Invariants hold under any generated operation sequence

- **WHEN** an arbitrary generated sequence of register, resolve, and enumerate
  operations — including concurrent batches with deliberate duplicate and
  divergence races — is executed against one registry
- **THEN** every accepted registration is present exactly once, every refusal
  is the stated typed error, resolution never observes a partial record, and
  enumeration stays deterministic — for every generated sequence, not only
  named examples

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
