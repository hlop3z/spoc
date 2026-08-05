# Component Registry — Delta

## ADDED Requirements

### Requirement: One object, one identity — divergence is loud

An object already present in the registry MUST be re-registerable only under
its existing identity: such a registration succeeds idempotently and returns
the existing record. Registering an already-registered object under a
different identity MUST fail with an error naming both the existing and the
requested identifier. The registry never silently answers a registration with
a record whose identity differs from what the caller stated.

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

### Requirement: Registration is safe under concurrency

Concurrent registrations MUST each be atomic: every accepted registration is
fully visible, no accepted registration is lost, and the duplicate-identifier
and identity-divergence guarantees hold under any interleaving. Enumeration
and resolution running concurrently with registration MUST observe only
complete records — never a partially constructed one.

#### Scenario: Parallel registration loses nothing

- **WHEN** many threads concurrently register distinct components
- **THEN** after all complete, every component is present in the registry
  exactly once

#### Scenario: Racing duplicates resolve to one winner

- **WHEN** two threads concurrently register different objects under the same
  identifier
- **THEN** exactly one registration succeeds and the other fails with the
  duplicate-identifier error naming the identifier and the winning object
