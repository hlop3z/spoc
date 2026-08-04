# project-scaffolding Specification

## Purpose
TBD - created by archiving change project-scaffolder. Update Purpose after archive.
## Requirements
### Requirement: Generating a runnable project

A single scaffolding operation MUST produce a complete project that starts successfully
without any edit to the generated content. The generated project MUST include the declarative
configuration file, the framework declaration, one app, and an entry point, and the names used
across them MUST agree: every kind named in the declaration has a corresponding module in the
generated app, and the app named in the configuration exists on disk.

#### Scenario: Generated project starts unedited

- **WHEN** a project is generated into an empty directory and started with no modifications
- **THEN** start succeeds, and the registry contains a component for each declared kind in the
  generated app

#### Scenario: Generated names agree across files

- **WHEN** a project is generated with a given set of kinds
- **THEN** the configuration's app list, the app directory on disk, and the modules within it
  all reflect those kinds and that app name consistently, with no name appearing in one file
  that is absent from another

#### Scenario: The generated app is a usable example

- **WHEN** a generated project is inspected
- **THEN** the app contains one module per declared kind, each holding a declared component,
  so it serves as the worked example for adding further apps by hand

#### Scenario: Target directory must be empty or absent

- **WHEN** a project is generated into a directory that already contains content
- **THEN** the operation fails naming the directory, and no file is created or modified

### Requirement: Generation never destroys existing content

The scaffolding operation MUST refuse to overwrite content it did not create. On refusal it
MUST name the conflicting path. An operation that fails partway MUST NOT leave content in a
state where some files were written and others were not.

#### Scenario: Conflicting target

- **WHEN** generation targets a location holding an existing file the plan would write
- **THEN** the operation fails naming that path, and the existing content is unchanged

#### Scenario: Failure leaves nothing behind

- **WHEN** a scaffolding operation fails after some content would have been written
- **THEN** the target contains no partially written files from that operation

### Requirement: Names are validated before writing

Project and app names supplied by the user MUST be validated against the same identity grammar
the kernel enforces for object names, and MUST be rejected before any content is written. A
name that would escape the target directory MUST be rejected.

#### Scenario: Invalid name rejected

- **WHEN** generation is requested with a name that does not satisfy the identity grammar
- **THEN** the operation fails naming the offending value and the grammar it must satisfy, and
  nothing is written

#### Scenario: Traversal rejected

- **WHEN** a name is supplied that would resolve outside the target directory
- **THEN** the operation fails and nothing is written outside that directory

### Requirement: The scaffolder does not alter the kernel's dependency footprint

The scaffolder MUST NOT cause the kernel to acquire any dependency, and the kernel MUST NOT
depend on the scaffolder at runtime. The dependency direction MUST run one way, so removing the
scaffolder leaves the kernel intact.

#### Scenario: Install footprint unchanged

- **WHEN** the kernel is installed
- **THEN** the acquired dependency set is unchanged from the kernel's stated guarantee, whether
  or not the scaffolder is present

#### Scenario: Kernel does not reference the scaffolder

- **WHEN** a project is started
- **THEN** no scaffolding capability is imported or referenced at runtime

#### Scenario: Scaffolder is removable

- **WHEN** the scaffolder is removed from the distribution
- **THEN** the kernel continues to start projects and pass its own suite unchanged

