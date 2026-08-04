## ADDED Requirements

### Requirement: Generating a runnable project

A single scaffolding operation MUST produce a complete project that starts successfully
without any edit to the generated content. The generated project MUST include the declarative
configuration file, the framework declaration, at least one app, and an entry point, and the
names used across them MUST agree: every kind named in the declaration has a corresponding
module in every generated app, and every app named in the configuration exists on disk.

#### Scenario: Generated project starts unedited

- **WHEN** a project is generated into an empty directory and started with no modifications
- **THEN** start succeeds, and the registry contains a component for each declared kind in the
  generated app

#### Scenario: Generated names agree across files

- **WHEN** a project is generated with a given set of kinds
- **THEN** the configuration's app list, the app directories on disk, and the modules within
  each app all reflect those kinds and app names consistently, with no name appearing in one
  file that is absent from another

#### Scenario: Target directory must be empty or absent

- **WHEN** a project is generated into a directory that already contains content
- **THEN** the operation fails naming the directory, and no file is created or modified

### Requirement: Adding an app to an existing project

Adding an app MUST create the app with one module per kind declared by that project's
framework, and MUST register the app in the configuration's app list for a selected mode.
The kinds used MUST be read from the project being modified rather than assumed, so an app
added to a framework declaring different kinds gets that framework's modules.

#### Scenario: App is created and registered together

- **WHEN** an app is added to an existing project
- **THEN** the app exists on disk with a module for each declared kind, and the configuration
  lists it under the selected mode

#### Scenario: Kinds come from the target project

- **WHEN** an app is added to a project whose framework declares kinds different from the
  scaffolder's own defaults
- **THEN** the created app contains a module for each of that project's declared kinds and no
  others

#### Scenario: Mode selection

- **WHEN** an app is added without a mode being specified
- **THEN** it is registered under the development mode list

#### Scenario: Adding to a directory that is not a project

- **WHEN** an app is added in a location with no discoverable configuration file
- **THEN** the operation fails naming the expected configuration location, and nothing is
  written

### Requirement: Generation never destroys existing content

Every scaffolding operation MUST refuse to overwrite content it did not create. On refusal it
MUST name the conflicting path. An operation that fails partway MUST NOT leave the project in
a state where some files were written and others were not.

#### Scenario: Conflicting app name

- **WHEN** an app is added whose name matches an app that already exists
- **THEN** the operation fails naming the existing app, and the existing app's contents are
  unchanged

#### Scenario: Failure leaves nothing behind

- **WHEN** a scaffolding operation fails after some content would have been written
- **THEN** the project contains no partially written files from that operation

### Requirement: Generated names are validated before writing

Project and app names supplied by the user MUST be validated against the same identity grammar
the kernel enforces for object names, and MUST be rejected before any content is written. A
name that would escape the target directory MUST be rejected.

#### Scenario: Invalid name rejected

- **WHEN** an app is requested with a name that does not satisfy the identity grammar
- **THEN** the operation fails naming the offending value and the grammar it must satisfy, and
  nothing is written

#### Scenario: Traversal rejected

- **WHEN** a name is supplied that would resolve outside the target directory
- **THEN** the operation fails and nothing is written outside that directory

### Requirement: The scaffolder is an opt-in surface

The scaffolder MUST NOT be required in order to run the kernel. Installing the kernel alone
MUST NOT acquire any dependency that exists solely to serve scaffolding, and the kernel MUST
start normally in an environment where the scaffolder is absent.

#### Scenario: Kernel install stays dependency-free

- **WHEN** the kernel is installed without opting into the scaffolder
- **THEN** no scaffolding dependency is acquired, and the installed dependency set is unchanged
  from the kernel's stated guarantee

#### Scenario: Kernel runs without the scaffolder present

- **WHEN** a project is started in an environment where the scaffolder is not installed
- **THEN** start succeeds and no scaffolding capability is referenced at runtime
