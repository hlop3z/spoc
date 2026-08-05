# Project Configuration

## Purpose

One declarative file configures the project: mode, the per-mode app cascade,
plugins, and per-mode environment values. The kernel reads nothing else — a
user's own settings module stays theirs — so what the system loads is
answerable by reading a single file.

## Requirements

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

Apps MUST be declared per mode, and the effective app list MUST cascade
according to a declared mode set. The mode set and each mode's cascade order
MUST be declarable in the configuration file; when the configuration declares
none, the default mode set applies: production includes only production apps;
staging includes staging then production; development includes development,
then staging, then production. Order is preserved and duplicates keep first
position. The active mode and every app-group key MUST name a mode in the
effective mode set; an unknown mode MUST fail start naming the valid modes.

#### Scenario: Development includes everything

- **WHEN** the configuration declares production `[auth]`, staging `[admin]`,
  development `[demo]` and the mode is `development`
- **THEN** the effective app list is `demo, admin, auth` in that order

#### Scenario: Production includes only production

- **WHEN** the same configuration runs in `production` mode
- **THEN** the effective app list is exactly `auth`

#### Scenario: Custom mode set

- **WHEN** the configuration declares a mode `test` whose cascade is
  `test, production`, with test apps `[fixtures]` and production apps
  `[auth]`, and the mode is `test`
- **THEN** the effective app list is `fixtures, auth` in that order

#### Scenario: Unknown mode fails naming the valid set

- **WHEN** the active mode or an app-group key names a mode outside the
  effective mode set
- **THEN** start fails with an error naming the offending mode and the modes
  that are valid

### Requirement: Apps are declared by module path

Every app entry MUST be a dotted module path importable by the language's
normal import mechanism from the environment the project runs in. The
component namespace for an app derives from the final segment of its declared
path, and that segment MUST conform to the identity grammar's namespace rule.
An app path that cannot be imported MUST fail start naming the path; the
kernel MUST NOT alter the import environment to make a path resolvable.

#### Scenario: Namespace derives from the final segment

- **WHEN** an app is declared as `myproject.apps.blog` and its modules declare
  components
- **THEN** those components register under namespace `blog`

#### Scenario: Unimportable app path

- **WHEN** a declared app path cannot be imported
- **THEN** start fails with an error naming the declared path

#### Scenario: Final segment must satisfy the grammar

- **WHEN** a declared app path's final segment violates the namespace grammar
- **THEN** start fails with an error naming the segment and the grammar

### Requirement: Plugins are configured registrations

Plugin references MUST be declared in the same declarative file, grouped by kind.
Each group MUST name a kind the framework declares — configuration is a second way
to populate the registry, never a second registry or a way to widen the closed kind
set. Each loaded object MUST be registered in the component registry under the
canonical grammar: the group as the kind, the reference's top-level package as the
namespace, and the object name derived from the reference's attribute the same way
discovery derives names. A plugin reference that cannot be resolved MUST fail
start, naming the reference; a group naming an undeclared kind MUST fail start,
naming the kind and the valid candidates.

#### Scenario: Declared plugin registers in the registry

- **WHEN** the configuration declares a plugin group naming a declared kind, with one
  resolvable reference
- **THEN** after start the loaded object is resolvable from the registry under
  `group:package.attribute_name`, and enumerating that kind includes its record

#### Scenario: Plugin group must name a declared kind

- **WHEN** the configuration declares a plugin group that is not a declared kind
- **THEN** start fails with an error naming the group and the declared kinds

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
