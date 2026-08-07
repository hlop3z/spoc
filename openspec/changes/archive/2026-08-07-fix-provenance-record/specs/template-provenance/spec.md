## MODIFIED Requirements

### Requirement: A generated project records its origin

A project generation MUST emit a record of the template set reference it was generated from and,
when that reference resolved to an exact revision, that revision. The record MUST be part of the
generation plan, so it is subject to the same never-overwrite and all-or-nothing guarantees as
every other generated file.

Emitting the record MUST be the generating operation's own obligation, discharged independently
of the rendered template set's declared shape. A template set MUST NOT be able to prevent the
record from being emitted by declining to declare it, and MUST NOT be able to supply, alter, or
substitute into its content. Every value the record states MUST originate from how the reference
was resolved, never from content the template set carries.

The record MUST be stored as data in a declarative format, readable without executing the
generated project. It MUST NOT affect whether the generated project starts.

The record MUST be a file of its own rather than an addition to the generated project's
configuration, so that an operation which adds to an existing project leaves that project's
configuration byte-identical.

#### Scenario: Origin is recorded for every generation

- **WHEN** a project is generated from any template set reference
- **THEN** the generated project contains a record naming the reference used

#### Scenario: A template set that declares no record still produces one

- **WHEN** a project is generated from a template set whose declared shape contains no origin
  record
- **THEN** the generated project still contains the record, naming the reference used, listed
  among the generated files

#### Scenario: Origin is recorded whoever authored the template set

- **WHEN** a project is generated from a template set authored outside the local system
- **THEN** the record is emitted with the same content it would carry for a built-in set, and
  nothing the retrieved set carries appears in it

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

#### Scenario: Adding to a project does not disturb its configuration

- **WHEN** an app is added to an existing generated project
- **THEN** the project's configuration file is unchanged, and the origin record is neither
  rewritten nor consulted for anything but the divergence comparison

## ADDED Requirements

### Requirement: The origin record's location is reserved

The destination the origin record occupies within a generated project MUST be reserved to the
generating operation. No template set may declare content that lands there, whatever its origin
or author.

A template set that claims the reserved destination MUST be refused before anything is written,
naming the reserved destination, in the same way any other invalid template set is refused. The
refusal MUST NOT depend on the set's origin: a built-in set claiming it fails exactly as a
retrieved one does.

#### Scenario: A template set claiming the reserved destination is refused

- **WHEN** an operation runs against a template set whose declared shape includes a file whose
  destination is the origin record's
- **THEN** the operation fails naming that destination as reserved, and nothing is written

#### Scenario: The reserved destination cannot be claimed by a retrieved set

- **WHEN** a template set obtained from outside the local system declares a file at the reserved
  destination
- **THEN** the operation fails identically to the same declaration in a built-in set, and no
  content the retrieved set carries reaches the record
