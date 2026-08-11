# Project Scaffolding — Delta

## MODIFIED Requirements

### Requirement: Generating a runnable project

A single scaffolding operation MUST produce a complete project that starts successfully
without any edit to the generated content. The generated project MUST include the declarative
configuration file, the framework declaration, one app, an entry point, and a record of the
template set it was generated from, and the names used across them MUST agree: every kind named
in the declaration has a corresponding module in the generated app, and the app named in the
configuration exists on disk.

Where generation derives a source-level name from a declared name, the derived name MUST be
legal in the generated language and MUST be distinct from every other derived name in the
same project. No name the identity grammar accepts may be refused on the grounds that the
generated language reserves it; the derivation MUST accommodate it instead.

The origin record MUST NOT affect whether the generated project starts, so a project remains
runnable if it is removed.

#### Scenario: Generated project starts unedited

- **WHEN** a project is generated into an empty directory and started with no modifications
- **THEN** start succeeds, and the registry contains a component for each declared kind in the
  generated app

#### Scenario: Generated names agree across files

- **WHEN** a project is generated with a given set of kinds
- **THEN** the configuration's app list, the app directory on disk, and the modules within it
  all reflect those kinds and that app name consistently, with no name appearing in one file
  that is absent from another

#### Scenario: A declared kind the generated language reserves

- **WHEN** a project is generated with a kind whose name is a reserved word in the generated
  language, or whose derived name would be one
- **THEN** generation succeeds, the derived name is a legal identifier, and the project starts
  unedited with that kind registered under the name as declared

#### Scenario: Derived names never collide

- **WHEN** a project is generated with kinds whose derived names would otherwise coincide
- **THEN** each kind receives a distinct derived name, and no declaration in the generated
  project is bound twice

#### Scenario: The generated app is a usable example

- **WHEN** a generated project is inspected
- **THEN** the app contains one module per declared kind, each holding a declared component,
  so it serves as the worked example for adding further apps by hand

#### Scenario: Target directory must be empty or absent

- **WHEN** a project is generated into a directory that already contains content
- **THEN** the operation fails naming the directory, and no file is created or modified

#### Scenario: Generation records its origin

- **WHEN** a project is generated from any template set reference
- **THEN** the generated project includes a record of that reference, listed among the generated
  files like any other

#### Scenario: Removing the origin record leaves a runnable project

- **WHEN** the origin record is deleted from a generated project and the project is started
- **THEN** start succeeds unchanged
