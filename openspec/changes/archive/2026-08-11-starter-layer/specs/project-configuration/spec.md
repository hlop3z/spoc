# Project Configuration — Delta

## MODIFIED Requirements

### Requirement: One declarative configuration source

The kernel MUST read project configuration — mode, per-mode app lists, and plugin
lists — from exactly one declarative configuration file at a conventional location
under the project root. The kernel MUST NOT require, read, or execute any other
configuration file; anything else in the project's config directory belongs to the
user and is ignored by the kernel.

The configuration table's key set is closed: a key outside the declared set MUST fail
start with a configuration error naming the unknown key and the valid keys, so a typo
never silently boots the project with defaults.

The kernel claims exactly one top-level table in the configuration file — its own.
Every other top-level table is application-owned: the kernel MUST expose such tables
to the application, as parsed data, through the framework's exposed configuration, and
MUST NOT interpret, validate, or act on their contents. The kernel MUST NOT silently
discard any top-level table. The kernel MUST NOT claim any additional top-level table
in the future; the single claimed table is a stated contract, so an application-owned
table can never collide with a kernel one.

A configuration file that exists but cannot be read or parsed MUST fail start with a
configuration error naming the path and the reason; no lower-level filesystem or
parser failure escapes as itself.

Loaded configuration is isolated per load: mutating the configuration one framework
exposes — including an application-owned table — MUST NOT alter the documented
defaults or the values observed by any later load in the same process.

All configuration warnings MUST obey one verbosity control: the missing-file warning
and the environment-file warnings are gated by the same setting, not each by its own
rule.

#### Scenario: Only the declarative file is consulted

- **WHEN** a project contains the declarative configuration file and an arbitrary
  user-owned settings module side by side
- **THEN** the kernel's behavior is fully determined by the declarative file, and
  deleting the user module changes nothing about discovery

#### Scenario: Missing configuration file

- **WHEN** start runs against a project root with no configuration file at the
  conventional location
- **THEN** the framework starts with documented defaults (development mode, no apps,
  no plugins) and emits a warning naming the expected location, subject to the same
  verbosity control as every other configuration warning

#### Scenario: Unknown configuration key is refused

- **WHEN** the configuration file contains a key outside the declared key set (for
  example a misspelling of a valid key) inside the kernel's own table
- **THEN** start fails with a configuration error naming the unknown key and listing
  the valid keys

#### Scenario: Unreadable configuration file is a configuration error

- **WHEN** the configuration file exists but cannot be read
- **THEN** start fails with a configuration error naming the path and the reason, not
  a raw filesystem error

#### Scenario: Defaults are isolated across loads

- **WHEN** a caller mutates the configuration mapping a started framework exposes, and
  a second framework is then constructed and started without a configuration file
- **THEN** the second framework observes the documented defaults, unaffected by the
  mutation

#### Scenario: An application-owned table reaches the application

- **WHEN** the configuration file declares a top-level table other than the kernel's
  own, and the framework starts
- **THEN** the application can read that table's parsed contents through the
  framework's exposed configuration, and the kernel's behavior is unaffected by those
  contents

#### Scenario: Application-owned tables are not validated by the kernel

- **WHEN** an application-owned table contains any keys and values whatsoever
- **THEN** start does not fail on their account, and the values are delivered as
  parsed

#### Scenario: Application-owned tables are isolated across loads

- **WHEN** a caller mutates an application-owned table exposed by one started
  framework, and a second framework is then constructed against the same project
- **THEN** the second framework observes the table as declared in the file, unaffected
  by the mutation
