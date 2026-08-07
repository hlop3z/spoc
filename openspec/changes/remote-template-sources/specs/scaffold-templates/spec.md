## MODIFIED Requirements

### Requirement: A template set is replaceable

A framework built on the kernel MUST be able to supply its own template set and obtain the same
scaffolding operation against it, without modifying the scaffolder. The selected template set
MUST be identified explicitly, and exactly one MUST be in effect for any single operation.

A template set reference MUST resolve whether it designates a filesystem directory, an
importable package, or a remote location, including when an importable package is installed in a
form that is not a plain directory on disk. The built-in template set MUST resolve under the
same rule, so the scaffolder works however the distribution itself is installed.

Which of these forms a reference designates MUST be decided by an explicit discriminator in the
reference itself, evaluated in a fixed order, before any attempt is made to load from any of
them. Resolution MUST NOT depend on what happens to exist locally.

A reference retrieved from a remote location MUST yield a template set indistinguishable from a
local one thereafter: the same validation, the same substitution, and the same guarantees apply
to it, and no capability is available to a template set on the strength of its origin.

#### Scenario: Downstream template set is used

- **WHEN** a scaffolding operation is invoked naming a template set supplied by a downstream
  framework
- **THEN** the generated project matches that template set's declared shape, not the built-in
  one

#### Scenario: Default when none is named

- **WHEN** a scaffolding operation is invoked without naming a template set
- **THEN** the built-in template set is used

#### Scenario: Unknown template set

- **WHEN** an operation names a template set that cannot be resolved
- **THEN** the operation fails naming the reference and listing the resolvable candidates, and
  nothing is written

#### Scenario: An importable package is a valid template set

- **WHEN** a template set is registered as an importable package rather than a
  filesystem directory
- **THEN** the scaffolding operation resolves it and generates against it, identically
  to a directory-backed set

#### Scenario: Non-directory installation still resolves

- **WHEN** the distribution providing a template set (including the built-in one) is
  installed in a form that is not a plain directory on disk
- **THEN** the template set still resolves and the scaffolding operation succeeds

#### Scenario: A directory path is a valid template set reference

- **WHEN** a scaffolding operation names a template set by a filesystem path to a
  directory containing a valid manifest
- **THEN** the operation resolves that directory and generates against it, identically
  to an installed set — and a path to a directory without a valid manifest fails naming
  what was missing, writing nothing

#### Scenario: A remote location is a valid template set reference

- **WHEN** a scaffolding operation names a template set by a reference designating a remote
  location containing a valid manifest
- **THEN** the operation resolves it and generates against it, identically to a local set — and
  a remote location without a valid manifest fails naming what was missing, writing nothing

#### Scenario: Form is decided before existence is consulted

- **WHEN** a reference whose form designates one kind of source is supplied, and a source of a
  different kind happens to exist under the same literal spelling
- **THEN** the reference resolves to the kind its form designates, and the coincidental source is
  never consulted

### Requirement: Substitution values are declared

The values a template set may substitute MUST be a declared, enumerable set rather than
arbitrary evaluation of the template content. Rendering a template set MUST NOT execute code
carried by that template set.

This holds regardless of the template set's origin and regardless of who authored it. A template
set obtained from outside the local system MUST NOT gain any ability to execute, to run a hook,
to evaluate an expression, or to influence generation other than by supplying declared
substitution values. This is a guarantee stated to the caller, not merely a property of the
implementation: a caller MUST be able to rely on it when deciding whether to name a reference
whose author they do not know.

#### Scenario: Declared values are enumerable

- **WHEN** a template set is inspected
- **THEN** the substitution values it depends on can be listed without rendering it

#### Scenario: Template content is not executed

- **WHEN** a template set contains content that would be executable in the emitted format
- **THEN** that content is emitted verbatim into the generated project and is not executed
  during generation

#### Scenario: Origin grants no additional capability

- **WHEN** a template set obtained from a remote location is rendered
- **THEN** no content it carries is executed, no hook mechanism is available to it, and its
  influence on generation is confined to the declared substitution values, identically to a
  built-in set

#### Scenario: Undeclared placeholder is still refused in retrieved content

- **WHEN** a template set obtained from a remote location uses a placeholder its manifest does
  not declare
- **THEN** the operation fails naming the placeholder and the template that used it, and nothing
  is written
