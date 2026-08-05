# Project Diagnostics

## Purpose

A project's declaration is validated before runtime and its registry is
inspectable without writing a script: check gathers every problem the first
boot would raise, with the kernel's own precision; list and explain
enumerate and resolve records. All operations are library-first and fully
isolated — nothing a diagnostic run imports or registers outlives it.

## Requirements

### Requirement: Pre-runtime project validation
The system MUST provide a check operation that, given a project directory,
validates the project's configuration and declaration without leaving any
running state behind: configuration syntax and typing, mode validity against
the declared cascade, resolvability of every declared app and plugin
reference, kind dependency acyclicity, identity uniqueness, and lifecycle
hook compatibility with the synchronous path. Every finding MUST carry the
same precision as the corresponding runtime failure — the failing segment
and, where applicable, the valid candidates.

#### Scenario: Clean project passes
- **WHEN** the check operation runs against a project whose declaration and configuration are valid
- **THEN** it reports success, and afterward no framework state, loaded app modules, or import-path changes remain

#### Scenario: Unresolvable app reference is reported before runtime
- **WHEN** the configuration declares an app whose module cannot be imported
- **THEN** the check reports the failing reference by name without the project ever serving traffic

#### Scenario: Configuration problems are reported with precision
- **WHEN** the configuration states a mode absent from the declared cascade, or an app list of the wrong type
- **THEN** the check names the offending key and value exactly as the runtime failure would

#### Scenario: Coroutine hooks under a sync start are flagged
- **WHEN** a declared lifecycle hook is a coroutine and the project's entry point starts synchronously
- **THEN** the check flags the hook by name instead of leaving the refusal to first boot

#### Scenario: Exit status reflects the outcome
- **WHEN** the check operation is invoked from the command line
- **THEN** the process exits zero on a clean report and non-zero when any finding was reported

### Requirement: Registry enumeration
The system MUST provide a list operation that boots the project's
declaration, enumerates every registered record's canonical identifier —
optionally narrowed by kind or namespace facet — and tears the boot down
completely before returning.

#### Scenario: All identifiers listed
- **WHEN** the list operation runs against a valid project
- **THEN** every registered component's canonical identifier is reported, in deterministic order

#### Scenario: Facet narrowing
- **WHEN** the list operation is narrowed to one kind
- **THEN** only that kind's identifiers are reported, and an unknown kind fails naming the valid kinds

### Requirement: Record explanation
The system MUST provide an explain operation that resolves one canonical
identifier and reports the record's facets (kind, namespace, object name)
and the identity of the registered object behind it. Resolution failures
MUST be the kernel's own precise errors — a typo never degrades to an empty
result.

#### Scenario: Known identifier explained
- **WHEN** the explain operation is given a registered identifier
- **THEN** the record's kind, namespace, object name, and the registered object's location are reported

#### Scenario: Unknown identifier fails with candidates
- **WHEN** the explain operation is given an identifier whose final segment does not exist
- **THEN** the failure names the failing segment and the valid candidates, and the process exit status is non-zero

### Requirement: Framework location by convention
The operations MUST locate the project's framework declaration by the same
convention the project generator emits, and MUST accept an explicit override
naming the module and attribute for projects shaped differently. A project
whose declaration cannot be located MUST be told what was looked for and how
to override it.

#### Scenario: Generated project needs no flags
- **WHEN** any diagnostic operation runs in a directory produced by the project generator
- **THEN** the framework declaration is found without additional arguments

#### Scenario: Override for custom layouts
- **WHEN** the caller states the module and attribute holding the framework
- **THEN** the operations use that declaration instead of the convention

#### Scenario: Missing declaration is actionable
- **WHEN** no framework declaration is found at the convention or the stated override
- **THEN** the failure states the location searched and the override syntax

### Requirement: Library-first invocability
Each diagnostic operation MUST be invocable as a plain library call with
structured results; the command-line surface only parses arguments, invokes
the same operation, and renders the result.

#### Scenario: Same result either way
- **WHEN** a diagnostic operation is invoked as a library call and via the command line against the same project
- **THEN** both report the same findings
