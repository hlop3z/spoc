# template-provenance Specification

## Purpose

What a generated project records about its own origin, and how a later scaffolding operation
against that project uses it. The record exists so an operation that adds to a project can
notice that the template set it is about to render is not the one that produced the project —
emitting a mismatched shape silently is the failure this prevents.

The record is advisory throughout. Nothing reads it at runtime, and no operation fails because
it is absent, unreadable, or disagrees.

## Requirements

### Requirement: A generated project records its origin

A project generation MUST emit a record of the template set reference it was generated from and,
when that reference resolved to an exact revision, that revision. The record MUST be part of the
generation plan, so it is subject to the same never-overwrite and all-or-nothing guarantees as
every other generated file.

The record MUST be stored as data in a declarative format, readable without executing the
generated project. It MUST NOT affect whether the generated project starts.

#### Scenario: Origin is recorded for every generation

- **WHEN** a project is generated from any template set reference
- **THEN** the generated project contains a record naming the reference used

#### Scenario: Resolved revision is recorded

- **WHEN** a project is generated from a reference that resolved to an exact revision
- **THEN** the record states that revision, sufficient to reproduce the same generation

#### Scenario: A set that cannot move records no revision

- **WHEN** a project is generated from a template set that has no revision, such as a built-in
  set or a local directory
- **THEN** the record names the reference and states no revision

#### Scenario: The record is ordinary generated content

- **WHEN** a generation that would emit the record fails for any reason
- **THEN** the record is not written, consistent with nothing else being written

#### Scenario: The record is readable as data

- **WHEN** the record is inspected
- **THEN** its content is parseable without running the generated project or its framework

#### Scenario: Removing the record leaves a runnable project

- **WHEN** the record is deleted from a generated project and the project is started
- **THEN** start succeeds unchanged

### Requirement: Divergence from the recorded origin is surfaced

An operation that adds to an existing project MUST compare the template set it is about to
render against the project's recorded origin. When they differ, the operation MUST report the
divergence, naming both the recorded origin and what is about to be rendered.

The operation MUST NOT fail on divergence alone — a project MAY legitimately draw from more than
one template set — but MUST NOT proceed silently.

A record that cannot be read MUST be treated as absent rather than as a failure, so an
unreadable note never prevents an unrelated operation.

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

#### Scenario: Unreadable record is treated as absent

- **WHEN** an app is added to a project whose origin record cannot be parsed
- **THEN** the operation proceeds and states that the project's origin is unknown

#### Scenario: A missing revision on one side is not divergence

- **WHEN** an app is added from the same reference the project records, where one side names a
  revision and the other has none
- **THEN** no divergence is reported
