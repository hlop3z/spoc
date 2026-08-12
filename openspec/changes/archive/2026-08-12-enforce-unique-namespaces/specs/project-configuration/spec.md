## MODIFIED Requirements

### Requirement: Apps are declared by module path

Every app entry MUST be a dotted module path importable by the language's
normal import mechanism from the environment the project runs in, optionally
followed by an explicit namespace. The component namespace for an app derives from
the final segment of its declared path unless the entry states one explicitly, and the
namespace — derived or stated — MUST conform to the identity grammar's namespace rule.
An app path that cannot be imported MUST fail start naming the path; the
kernel MUST NOT alter the import environment to make a path resolvable.

Two installed apps MUST NOT resolve to the same namespace. Because the namespace derives
from a path's final segment, apps at different paths under different parents can collide
on that segment; such a collision MUST fail start, naming the contested namespace and both
declared paths, rather than registering both apps' components into one namespace. The
explicit form exists to resolve exactly this without renaming a package the author may not
control.

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

#### Scenario: Two apps deriving the same namespace

- **WHEN** two apps are declared whose paths differ but whose final segments are both
  `shop`
- **THEN** start fails with an error naming the namespace `shop` and both declared paths
- **AND** no component of either app is registered

#### Scenario: An explicit namespace resolves the collision

- **WHEN** two apps whose final segments collide are declared, and one entry states an
  explicit namespace distinct from the other's
- **THEN** start succeeds
- **AND** that app's components register under the stated namespace rather than the
  derived one

#### Scenario: An explicit namespace must satisfy the grammar

- **WHEN** an app entry states an explicit namespace that violates the namespace grammar
- **THEN** start fails with an error naming the stated namespace and the grammar

#### Scenario: Two apps stating the same explicit namespace

- **WHEN** two app entries state the same explicit namespace
- **THEN** start fails naming the contested namespace and both declared paths, exactly as
  a derived collision does

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

A plugin reference MUST NOT claim a namespace another package already owns. Registering
into an installed app's own namespace from that app's package is the ordinary use of a
plugin group and MUST succeed; a reference whose package differs from the package that owns
the derived namespace MUST fail start, naming the namespace and both packages. An app
declared with an explicit namespace owns that namespace for this purpose, so a plugin
reference inside that app's package registers under the stated namespace, never the derived
one.

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

#### Scenario: Plugin contesting an installed app's namespace

- **WHEN** an app `apps.shop` is installed and a plugin reference `vendor.shop.extras.Hook`
  derives the same namespace `shop`
- **THEN** start fails with an error naming the namespace and both packages

#### Scenario: Plugin registering into its own app's namespace

- **WHEN** an app `apps.shop` is installed and a plugin reference `apps.shop.extras.Hook`
  derives the namespace `shop`
- **THEN** start succeeds and the object registers under namespace `shop`

#### Scenario: Plugin inside an app that stated an explicit namespace

- **WHEN** an app `vendor.shop` is declared with the explicit namespace `vendor_shop`, and
  a plugin reference `vendor.shop.extras.Hook` is declared
- **THEN** the object registers under namespace `vendor_shop`, the namespace its package
  owns
