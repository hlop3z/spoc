# Kind Vocabulary

## Purpose

The conventional default vocabulary: an enumerated set of kind names with agreed
meanings, presented as a default rather than a mandate. Any project may declare
any kinds it chooses; the vocabulary is what the documentation teaches, what the
starter generation emits, and what reusable third-party apps may assume — the
shared language an ecosystem needs, without a mechanism to enforce it. Its one
behavioral member is the resource lifecycle convention, expressed entirely
through existing public kernel contracts.

## Requirements

### Requirement: A conventional default vocabulary is published

The project MUST publish one conventional kind vocabulary: an enumerated set of kind
names, each with a stated meaning and a stated lifecycle role (declarative, or bound to
kind startup/shutdown hooks). The vocabulary MUST be presented as a default, not a
mandate: the documentation stating it MUST, in the same place, state that a project may
declare any kinds it chooses and that the vocabulary is what reusable third-party apps
may assume. Every kind name in the vocabulary MUST satisfy the identity grammar's kind
rule.

#### Scenario: The vocabulary is enumerable from the documentation

- **WHEN** a reader consults the published documentation for the vocabulary
- **THEN** they find one authoritative enumeration of the conventional kinds, each with
  its meaning and lifecycle role, and the deviation rule stated alongside it

#### Scenario: Vocabulary names satisfy the grammar

- **WHEN** each kind name in the published vocabulary is checked against the identity
  grammar
- **THEN** every name is a valid kind segment

### Requirement: Documentation and generation agree on the vocabulary

The kind names and their meanings MUST agree everywhere the project teaches or emits
the conventional vocabulary: in documentation, in shipped template sets that declare
it, and in the reference application where it demonstrates vocabulary conventions. A
kind taught under one meaning in one place MUST NOT appear under a different meaning in
another.

#### Scenario: A vocabulary kind means the same thing everywhere

- **WHEN** a kind from the conventional vocabulary appears in documentation and in a
  shipped template set's generated declaration
- **THEN** both use the same kind name for the same stated meaning

### Requirement: The resource lifecycle convention

The vocabulary MUST include a resource kind whose convention is: components of that kind
declare process-lifetime resources; the kind's startup hook makes each declared resource
live before application code runs; any component may reach a live resource through
normal registry resolution under the canonical grammar; and the kind's shutdown hook
releases each resource during teardown. The convention MUST be expressible entirely
through existing public kernel contracts — kind declaration, lifecycle hooks, and
registry resolution — with no dedicated resource API.

After the framework has shut down, resolving a resource identifier MUST fail with the
registry's named resolution error, never yield a released resource.

#### Scenario: A resource is live when application code runs

- **WHEN** a project declares a resource component under the convention and starts
- **THEN** by the time any dependent application code executes, resolving the resource's
  identifier returns the live resource

#### Scenario: A resource is released at shutdown

- **WHEN** a started project that opened a resource under the convention shuts down
- **THEN** the resource's release action has run by the time shutdown returns

#### Scenario: Resolution after shutdown fails loudly

- **WHEN** code resolves a resource identifier after the framework has shut down
- **THEN** resolution fails with a named error, and no released resource is returned
