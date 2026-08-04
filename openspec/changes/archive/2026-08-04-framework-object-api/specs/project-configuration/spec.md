# Project Configuration

## ADDED Requirements

### Requirement: One declarative configuration source

The kernel MUST read project configuration — mode, per-mode app lists, and plugin
lists — from exactly one declarative configuration file at a conventional location
under the project root. The kernel MUST NOT require, read, or execute any other
configuration file; anything else in the project's config directory belongs to the
user and is ignored by the kernel.

#### Scenario: Only the declarative file is consulted

- **WHEN** a project contains the declarative configuration file and an arbitrary
  user-owned settings module side by side
- **THEN** the kernel's behavior is fully determined by the declarative file, and
  deleting the user module changes nothing about discovery

#### Scenario: Missing configuration file

- **WHEN** start runs against a project root with no configuration file at the
  conventional location
- **THEN** the framework starts with documented defaults (development mode, no apps,
  no plugins) and emits a warning naming the expected location

### Requirement: Mode cascade for app lists

Apps MUST be declared per mode, and the effective app list MUST cascade:
production mode includes only production apps; staging includes staging then
production; development includes development, then staging, then production. Order is
preserved and duplicates keep first position.

#### Scenario: Development includes everything

- **WHEN** the configuration declares production `[auth]`, staging `[admin]`,
  development `[demo]` and the mode is `development`
- **THEN** the effective app list is `demo, admin, auth` in that order

#### Scenario: Production includes only production

- **WHEN** the same configuration runs in `production` mode
- **THEN** the effective app list is exactly `auth`

### Requirement: Plugins are configuration

Plugin references MUST be declared in the same declarative file, grouped by purpose,
each reference resolvable to a loadable object. A plugin reference that cannot be
resolved MUST fail start, naming the reference.

#### Scenario: Declared plugin loads

- **WHEN** the configuration declares a plugin group with one resolvable reference
- **THEN** after start the loaded plugin object is available under that group

#### Scenario: Unresolvable plugin

- **WHEN** a declared plugin reference names a module or attribute that does not exist
- **THEN** start fails with an error naming the reference

### Requirement: Mode-specific environment values

Environment values MUST load from per-mode files in a conventional environment
directory, falling back to a default file when no mode-specific file exists, and to
empty values when neither exists. The fallback MUST NOT depend on any logging or
verbosity setting.

#### Scenario: Fallback to default

- **WHEN** the environment directory contains only a default file and the mode is
  `production`
- **THEN** the default file's values are loaded

#### Scenario: No environment files

- **WHEN** no environment directory exists
- **THEN** environment values are empty and start still succeeds
