# Component Registry — delta

## MODIFIED Requirements

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
