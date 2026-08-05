# Project Configuration — Delta

## MODIFIED Requirements

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
