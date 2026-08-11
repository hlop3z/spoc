# Starter Templates

## ADDED Requirements

### Requirement: A starter template set ships with the distribution

The distribution MUST include, alongside the minimal default template set, one starter
template set resolvable by name under the same reference rules as the default. The
starter MUST be held to every existing template-set contract: declared data only, no
execution during generation, validated for completeness before anything is written.
Selecting it MUST be explicit; the minimal set remains the default when no set is named.

#### Scenario: The starter resolves by name

- **WHEN** a scaffolding operation names the starter template set
- **THEN** it resolves as a built-in set and generation proceeds against it under the
  same validation as any other set

#### Scenario: The minimal set remains the default

- **WHEN** a scaffolding operation names no template set
- **THEN** the minimal default set is used, not the starter

### Requirement: The starter generates a runnable, transport-neutral application

A project generated from the starter MUST start unedited and MUST declare the
conventional kind vocabulary. It MUST include: a transport-neutral projection module
that derives abstract surface tables from registry records alone; a runnable
project-owned command surface whose available commands are derived from registry
records through that projection; a resource declared, opened, and released under the
resource lifecycle convention; and a dispatch site through which surface-invoked hook
components run. The generated project MUST NOT require any third-party dependency to
start or to run its command surface, and it MUST NOT generate a binding to any
specific transport; binding the projection to a transport is left to the project.
Generating or running the starter MUST NOT add any runtime dependency to the kernel's
distribution.

#### Scenario: Generated starter starts unedited

- **WHEN** a project is generated from the starter into an empty directory and started
  with no modifications
- **THEN** start succeeds and the registry contains the generated components under the
  conventional vocabulary

#### Scenario: The generated project is dependency-free

- **WHEN** a generated starter project is started and its command surface is run in an
  environment containing only the language runtime and the kernel distribution
- **THEN** both succeed, and the kernel distribution's declared runtime dependencies
  are unchanged

#### Scenario: No transport is chosen for the project

- **WHEN** the generated project's files are inspected
- **THEN** no generated module imports or configures a specific serving, messaging, or
  worker framework; transport binding remains the project's decision

### Requirement: The starter's surfaces are registry projections

In a generated starter project, the projection module MUST derive its surface tables by
enumerating the registry — every projected entry corresponds to a registry record of
the appropriate conventional kind, and none is defined anywhere else — and the command
surface MUST expose exactly what the projection derives for the command kind.
Declaring one additional component of a projected kind in the generated app MUST
extend the projected tables, and the command surface where applicable, without editing
the projection or surface modules.

#### Scenario: Adding a component extends the surface

- **WHEN** one new component of the command kind is declared in the generated project
  and the project is restarted
- **THEN** the command surface exposes a corresponding new command, with no edit to the
  projection or surface modules

#### Scenario: Nothing is exposed outside the registry

- **WHEN** the projection module's derived tables are compared with the registry's
  records of the projected kinds
- **THEN** they correspond one-to-one
