## ADDED Requirements

### Requirement: Emission beyond the supported scale MUST be reported, not silent

The generator MUST report to the operator whenever the identifier-narrowed
description is produced for a registry larger than the scale the declared checker
set is known to support: the entry count, the documented threshold, and the
supported alternative surface. Generation MUST still produce the description — the report informs a
decision, it does not make one — and generation below the threshold MUST remain
silent on this subject.

#### Scenario: Past the threshold, the operator is told

- **WHEN** the identifier-narrowed description is generated for a registry whose
  entry count exceeds the documented threshold
- **THEN** the description is still written
- **AND** the report names the entry count, the threshold, and the alternative
  surface a larger registry should rely on

#### Scenario: Below the threshold, nothing changes

- **WHEN** the identifier-narrowed description is generated for a registry within
  the documented threshold
- **THEN** no scale report is produced
- **AND** the emitted description is byte-identical to what the generator produced
  before this requirement existed
