# Delta: documentation-integrity

## MODIFIED Requirements

### Requirement: Documentation code examples execute

Every code example in the published documentation MUST either be executed by the
project's test suite or carry an explicit, machine-readable non-runnable marker. An
example with neither MUST fail the test run — silence is not an allowed state.

Published documentation includes the repository README — the project front page and
the distribution long-description — not only the documentation site's pages. A
document read before the documentation site is held to the same bar as the site.

#### Scenario: A runnable example passes

- **WHEN** the test suite runs over the documentation
- **THEN** every unmarked code example is executed, and an example that raises is
  reported as a test failure naming the documentation file it came from

#### Scenario: A broken example cannot ship silently

- **WHEN** a documentation edit introduces a code example that no longer runs (missing
  import, renamed symbol, undefined variable)
- **THEN** the validation gate fails before the documentation is published

#### Scenario: A non-runnable fragment is explicit

- **WHEN** an example cannot be executed standalone (illustrative fragment, output-only
  block)
- **THEN** it carries a visible-in-source marker saying so, and the test suite counts it
  as intentionally skipped rather than passing

#### Scenario: An example needs a project tree

- **WHEN** an example presumes a project on disk (apps, configuration file)
- **THEN** the test suite supplies that tree through the project's own test harness and
  the example runs against it unmodified

#### Scenario: The README is inside the gate

- **WHEN** the test suite runs over the documentation
- **THEN** the README's code examples are collected and held to the same
  execute-or-marked-skip contract as the documentation site's pages

#### Scenario: An example never demonstrates what cannot work

- **WHEN** a documentation example shows a component being declared and then resolved
- **THEN** the example presents the declaration in the location discovery actually
  reads it from, and the executed example resolves successfully as shown
