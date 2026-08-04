## ADDED Requirements

### Requirement: The emitted shape is declared data

The content a scaffolding operation emits MUST be defined as data in files of the format they
are emitted as, not embedded as literals inside program code. Changing what a generated project
looks like MUST be possible by changing that data alone.

#### Scenario: Shape changes without code changes

- **WHEN** the declared shape is altered to add a file to the generated project
- **THEN** subsequent generations include that file, with no change to the scaffolder's own
  program code

#### Scenario: Emitted files carry their native format

- **WHEN** the declared shape is inspected
- **THEN** each item that becomes a configuration file, a module, or an environment file is
  stored in a file of that same format rather than as a string inside code

### Requirement: A template set is replaceable

A framework built on the kernel MUST be able to supply its own template set and obtain the same
scaffolding operation against it, without modifying the scaffolder. The selected template set
MUST be identified explicitly, and exactly one MUST be in effect for any single operation.

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

### Requirement: Template sets are validated before use

A template set MUST be checked for completeness before any content is written. A set that omits
an element the scaffolding operations require, or that declares a substitution value the
operation cannot supply, MUST fail naming what is missing.

#### Scenario: Incomplete template set

- **WHEN** an operation runs against a template set that omits a required element
- **THEN** the operation fails naming the missing element, and nothing is written

#### Scenario: Unsatisfiable substitution

- **WHEN** a template set declares a substitution value that the invoking operation does not
  supply
- **THEN** the operation fails naming that value, and nothing is written

### Requirement: Substitution values are declared

The values a template set may substitute MUST be a declared, enumerable set rather than
arbitrary evaluation of the template content. Rendering a template set MUST NOT execute code
carried by that template set.

#### Scenario: Declared values are enumerable

- **WHEN** a template set is inspected
- **THEN** the substitution values it depends on can be listed without rendering it

#### Scenario: Template content is not executed

- **WHEN** a template set contains content that would be executable in the emitted format
- **THEN** that content is emitted verbatim into the generated project and is not executed
  during generation
