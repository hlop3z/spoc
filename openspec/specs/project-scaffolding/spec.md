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

Escape detection MUST cover every path form the host platform resolves: relative
traversal spelled with either separator, absolute paths, and drive- or root-qualified
forms. The rejection happens in the validation step, before any filesystem operation —
not only at a final write barrier — and it applies equally to paths supplied by a
template set, so a third-party template cannot name a target outside the directory
being generated.

#### Scenario: Invalid name rejected

- **WHEN** generation is requested with a name that does not satisfy the identity grammar
- **THEN** the operation fails naming the offending value and the grammar it must satisfy, and
  nothing is written

#### Scenario: Traversal rejected

- **WHEN** a name is supplied that would resolve outside the target directory
- **THEN** the operation fails and nothing is written outside that directory

#### Scenario: Traversal with the platform's alternate separator is rejected

- **WHEN** a template entry or name spells parent-directory traversal with the host
  platform's alternate separator (for example a backslash)
- **THEN** validation rejects it before any filesystem operation, and nothing is written

#### Scenario: Drive- or root-qualified targets are rejected

- **WHEN** a template entry or name designates an absolute, drive-qualified, or
  root-qualified location
- **THEN** validation rejects it before any filesystem operation, and nothing is written
  outside the target directory

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

### Requirement: Adding an app to an existing project

A single operation MUST generate one additional app into an existing project: a package
whose shape matches what project generation emits — one module per kind, each holding a
declared component — so the new app registers successfully on the next boot once
configured. The operation MUST refuse to write when the app already exists, writing
nothing. The operation MUST NOT edit the project's configuration; it MUST state exactly
what the author adds to the configuration to install the app.

When the caller does not state the kinds, they MUST be derived from the project's own
framework declaration, so the author never restates what the project already declares;
stated kinds override derivation. If neither stated kinds nor a locatable declaration
exist, the operation MUST fail actionably, naming both paths.

#### Scenario: Generated app matches the project shape

- **WHEN** an app is added to a project whose declaration states a set of kinds
- **THEN** the new app package contains one module per kind, each holding a declared
  component, identical in shape to the app project generation emits

#### Scenario: Existing app is never overwritten

- **WHEN** an app is added under a name that already exists in the project
- **THEN** the operation fails naming the app, and no file is created or modified

#### Scenario: Configuration is stated, not edited

- **WHEN** an app is added successfully
- **THEN** the project's configuration file is byte-identical to before, and the output
  states the exact configuration entry that installs the new app

#### Scenario: Kinds derive from the declaration

- **WHEN** an app is added without stating kinds, in a project whose framework
  declaration is locatable by the stated convention
- **THEN** the generated modules match the declaration's kinds exactly

#### Scenario: No kinds and no declaration is actionable

- **WHEN** an app is added without stating kinds and no framework declaration can be
  located
- **THEN** the operation fails stating both how to state kinds and how the declaration
  is located
