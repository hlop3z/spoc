## ADDED Requirements

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
