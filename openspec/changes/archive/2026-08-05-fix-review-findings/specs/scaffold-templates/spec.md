# Scaffold Templates — delta

## MODIFIED Requirements

### Requirement: A template set is replaceable

A framework built on the kernel MUST be able to supply its own template set and obtain the same
scaffolding operation against it, without modifying the scaffolder. The selected template set
MUST be identified explicitly, and exactly one MUST be in effect for any single operation.

A template set reference MUST resolve whether it designates a filesystem directory or an
importable package, including when that package is installed in a form that is not a
plain directory on disk. The built-in template set MUST resolve under the same rule, so
the scaffolder works however the distribution itself is installed.

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
