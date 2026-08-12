## MODIFIED Requirements

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
