# documentation-integrity

The contract that published documentation cannot drift from the code it documents.
Snippets execute, reference listings derive from the source of truth, and failure
documentation covers the whole public error surface.

## ADDED Requirements

### Requirement: Documentation code examples execute

Every code example in the published documentation MUST either be executed by the
project's test suite or carry an explicit, machine-readable non-runnable marker. An
example with neither MUST fail the test run — silence is not an allowed state.

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

### Requirement: Examples show their result

A documentation example whose value is its output MUST display that output beside the
code, and the displayed output MUST be verified against actual execution.

#### Scenario: Output drift is caught

- **WHEN** a change alters what an executed example prints
- **THEN** the stale output block in the documentation is reported by the test suite,
  and regenerating it is a mechanical operation, not a manual edit

### Requirement: API reference derives from the declared public surface

The API reference's member listings MUST be derived from the package's own declaration
of its public surface, not maintained as a separate hand-written enumeration.

#### Scenario: A new export appears automatically

- **WHEN** a name is added to the package's declared public surface
- **THEN** the next documentation build lists it in the API reference with no
  documentation-side edit

#### Scenario: A removed export disappears

- **WHEN** a name is removed from the declared public surface
- **THEN** the next documentation build no longer lists it, leaving no ghost entry

### Requirement: CLI reference derives from the real command-line interface

The CLI reference page's commands, flags, and help text MUST be generated from the same
parser the shipped command uses, at documentation build time.

#### Scenario: A CLI change propagates

- **WHEN** a subcommand or flag is added, removed, or reworded in the CLI
- **THEN** the next documentation build reflects it without a hand edit to the CLI page

### Requirement: Every public exception is indexed

The documentation MUST contain an error index in which every publicly exported
exception type appears with what triggers it and how to resolve it, and the index MUST
be verified complete against the declared public surface.

#### Scenario: Looking up an error by name

- **WHEN** a user searches the documentation for the name of any public exception
- **THEN** the error index answers with the triggering condition, the fix, and a link to
  the page explaining the underlying concept

#### Scenario: A new exception cannot ship unindexed

- **WHEN** a new exception type is added to the public surface without an error-index
  entry
- **THEN** the validation gate reports the omission as a failure
