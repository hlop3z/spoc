## MODIFIED Requirements

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

#### Scenario: Invariants hold under any generated operation sequence

- **WHEN** an arbitrary generated sequence of register, resolve, and enumerate
  operations — including concurrent batches with deliberate duplicate and
  divergence races — is executed against one registry
- **THEN** every accepted registration is present exactly once, every refusal
  is the stated typed error, resolution never observes a partial record, and
  enumeration stays deterministic — for every generated sequence, not only
  named examples
