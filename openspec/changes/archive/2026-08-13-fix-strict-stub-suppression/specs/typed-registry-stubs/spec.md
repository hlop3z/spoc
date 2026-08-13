## ADDED Requirements

### Requirement: A generated description MUST be diagnostic-free under the declared checker set

A generated type description MUST produce no diagnostics when read by every type checker
in the project's declared conformance set, in every emission mode the generator offers.
Where a description deliberately deviates from a rule a checker enforces, the description
itself MUST carry the suppression, placed so that the checker honors it — a consumer MUST
NOT need to configure their checker, suppress anything on their side, or avoid a checker
in the set to use an emitted description cleanly.

Conformance MUST be verified against every emission mode, not asserted from the
generator's output text alone: a description generated in each mode is read by each
checker in the set, and any diagnostic on valid consuming code is a verification
failure.

#### Scenario: Every emission mode is verified against every checker

- **WHEN** conformance verification runs for the project
- **THEN** a description in each emission mode is checked by every type checker in the
  declared conformance set, against consuming code that is valid under that mode
- **AND** verification fails if any checker reports any diagnostic

#### Scenario: A suppression the checker does not honor is a failure, not a ship

- **WHEN** an emitted description carries an internal suppression placed where a checker
  in the declared set does not honor it, so that checker reports a diagnostic
- **THEN** verification fails before the description reaches a consumer

#### Scenario: Checker evolution is detected rather than inherited by consumers

- **WHEN** a checker in the declared set changes where or how it reports a diagnostic,
  such that a previously clean description no longer verifies
- **THEN** verification fails on the project's side
- **AND** the failure identifies the emission mode and checker that produced the
  diagnostic
