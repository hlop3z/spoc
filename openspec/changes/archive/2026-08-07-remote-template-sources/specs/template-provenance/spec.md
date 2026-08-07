## ADDED Requirements

### Requirement: A generated project records its origin

A project generation MUST emit a record of the template set reference it was generated from and,
when that reference resolved to an exact revision, that revision. The record MUST be part of the
generation plan, so it is subject to the same never-overwrite and all-or-nothing guarantees as
every other generated file.

The record MUST be stored as data in a declarative format, readable without executing the
generated project.

#### Scenario: Origin is recorded for every generation

- **WHEN** a project is generated from any template set reference
- **THEN** the generated project contains a record naming the reference used

#### Scenario: Resolved revision is recorded

- **WHEN** a project is generated from a reference that resolved to an exact revision
- **THEN** the record states that revision, sufficient to reproduce the same generation

#### Scenario: The record is ordinary generated content

- **WHEN** a generation that would emit the record fails for any reason
- **THEN** the record is not written, consistent with nothing else being written

#### Scenario: The record is readable as data

- **WHEN** the record is inspected
- **THEN** its content is parseable without running the generated project or its framework

### Requirement: Divergence from the recorded origin is surfaced

An operation that adds to an existing project MUST compare the template set it is about to
render against the project's recorded origin. When they differ, the operation MUST report the
divergence, naming both the recorded origin and what is about to be rendered.

The operation MUST NOT fail on divergence alone — a project MAY legitimately draw from more than
one template set — but MUST NOT proceed silently.

#### Scenario: Matching origin proceeds quietly

- **WHEN** an app is added rendering the same template set the project records
- **THEN** the operation proceeds and reports no divergence

#### Scenario: Divergent origin is reported

- **WHEN** an app is added rendering a template set differing from the project's recorded origin
- **THEN** the operation reports the divergence, naming the recorded origin and the template set
  being rendered, and then proceeds

#### Scenario: Absent record is reported, not fatal

- **WHEN** an app is added to a project that carries no origin record
- **THEN** the operation proceeds and states that the project's origin is unknown
