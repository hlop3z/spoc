# Project Configuration — delta

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

A configuration file that exists but cannot be read or parsed MUST fail start with a
configuration error naming the path and the reason; no lower-level filesystem or
parser failure escapes as itself.

Loaded configuration is isolated per load: mutating the configuration one framework
exposes MUST NOT alter the documented defaults observed by any later load in the same
process.

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
  example a misspelling of a valid key)
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

### Requirement: Plugins are configured registrations

Plugin references MUST be declared in the same declarative file, grouped by kind.
Each group MUST name a kind the framework declares — configuration is a second way
to populate the registry, never a second registry or a way to widen the closed kind
set. Each loaded object MUST be registered in the component registry under the
canonical grammar, read from the reference the same way discovery reads an app
layout: a reference is `<app-path>.<module>.<attribute>`, the group is the kind, the
namespace is the final segment of `<app-path>` (the segment immediately before the
module), and the object name derives from the attribute the same way discovery
derives names. A reference whose module path is a single segment uses that segment
as the namespace. The derived namespace MUST satisfy the namespace grammar. A plugin
reference that cannot be resolved MUST fail start, naming the reference; a group
naming an undeclared kind MUST fail start, naming the kind and the valid candidates.

A configured registration carries no metadata. A group naming a kind that declares a
component metadata contract MUST fail start with an error stating that configured
registrations cannot satisfy a metadata contract, naming the kind — not a generic
metadata violation that leaves the author searching for a way to supply it.

#### Scenario: Declared plugin registers in the registry

- **WHEN** the configuration declares a plugin group naming a declared kind, with one
  resolvable reference `pkg.extras.AuditHook`
- **THEN** after start the loaded object is resolvable from the registry under
  `group:pkg.audit_hook`, and enumerating that kind includes its record

#### Scenario: Plugin inside a dotted app path takes the app's namespace

- **WHEN** apps live under a container package and the configuration declares a
  plugin reference `apps.blog.extras.AuditHook` in a declared group
- **THEN** after start the object is resolvable under `group:blog.audit_hook` — the
  namespace is the app's final path segment, never the container package

#### Scenario: Top-level module is its own namespace

- **WHEN** the configuration declares a plugin reference `pkg.AuditHook`, whose module
  path is the single segment `pkg`
- **THEN** after start the object is resolvable under `group:pkg.audit_hook`

#### Scenario: Plugin group must name a declared kind

- **WHEN** the configuration declares a plugin group that is not a declared kind
- **THEN** start fails with an error naming the group and the declared kinds

#### Scenario: Unresolvable plugin

- **WHEN** a declared plugin reference names a module or attribute that does not exist
- **THEN** start fails with an error naming the reference

#### Scenario: Metadata-contract kinds refuse configured registration

- **WHEN** the configuration declares a plugin group naming a declared kind whose
  components carry a metadata contract
- **THEN** start fails with an error naming the kind and stating that configured
  registrations cannot satisfy a metadata contract
