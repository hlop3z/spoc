# Typed Registry Stubs

## Purpose

The project describes its own resolution surface as a static artifact, so an
editor and a type checker can tell a developer what `resolve` returns for each
identifier. The description is produced by dry-booting the project — registration
and discovery, no lifecycle — and is inert: nothing at runtime loads it, and
deleting it changes no behavior. It is deterministic, so it can be committed and
verified in CI rather than trusted.

## Requirements

### Requirement: Describing a project MUST NOT run it

Producing a static type description of a project's resolution surface MUST register its
applications and run discovery without invoking module initializers, teardown routines, or
any kind lifecycle hook. Describing a project MUST leave no observable effect that booting
it would not have left, and MUST return the framework to its pre-description state when it
completes, including after a failure.

#### Scenario: Initializers do not run during description

- **WHEN** a project whose modules record an observable effect on initialization is described
- **THEN** the description completes and reports every registered component
- **AND** no initializer, teardown, or lifecycle hook effect is observed

#### Scenario: Description leaves no residue

- **WHEN** a project is described and the framework is inspected afterwards
- **THEN** the framework reports itself not started
- **AND** a subsequent ordinary start succeeds unchanged

### Requirement: The description MUST cover every resolvable identifier

A generated type description MUST include one entry for every component the described
project registers, keyed by the component's canonical identifier, and MUST include no entry
for an identifier the project does not register. Each entry MUST state the static type a
consumer obtains when reading that record's object.

The set of described identifiers MUST be derived from the project's own registry
projection rather than from a separate enumeration of the registry, so that the stub and
every other description of one project cannot disagree about what it registered. Deriving
from the projection MUST NOT change what the description contains. The description MAY
carry language-specific information the projection does not — the static type each
identifier yields, and how an undescribable type degrades — because that information is
meaningful only to a type checker and does not belong in a language-neutral projection.

#### Scenario: Every registered component appears

- **WHEN** a project registering components across several kinds and namespaces is described
- **THEN** the description contains exactly one entry per registered canonical identifier
- **AND** contains no entry for any identifier that is not registered

#### Scenario: Components registered from configuration appear

- **WHEN** a project registers components through configuration rather than through module
  discovery
- **THEN** those components appear in the description on equal terms with discovered ones

#### Scenario: The description and the projection agree

- **WHEN** one project is both described as a type description and projected as data
- **THEN** the two cover exactly the same set of canonical identifiers, in the same order

#### Scenario: Language-specific detail stays in the description

- **WHEN** a project is projected as data
- **THEN** the projection carries each component's shape
- **AND** it does not carry the static type reference the description uses, which remains a
  property of the description alone

### Requirement: The description MUST distinguish the three component shapes

Each entry MUST record whether the registered object is constructible, a value, or a
callable, and MUST state a static type consistent with that shape: a constructible object's
entry describes the constructor, a value's entry describes the value, and a callable's entry
describes the call signature.

#### Scenario: A constructible component

- **WHEN** a component registered as a constructible object is described
- **THEN** its entry is marked constructible
- **AND** consuming that record's object statically offers the object's construction
  interface rather than an instance interface

#### Scenario: A callable component

- **WHEN** a component registered as a callable is described
- **THEN** its entry is marked callable
- **AND** the entry states the callable's parameters and result

### Requirement: An undescribable type MUST degrade rather than be guessed

When a registered object's static type cannot be determined faithfully, the entry MUST fall
back to the unconstrained type and MUST NOT substitute an inferred or approximate type. A
degraded entry MUST still be present and MUST still be resolvable by identifier.

#### Scenario: Unannotated callable

- **WHEN** a callable component carries no parameter or result type information
- **THEN** its entry is present with an unconstrained result
- **AND** no invented parameter or result type appears

#### Scenario: Degradation is reportable

- **WHEN** a project containing undescribable components is described
- **THEN** the count of degraded entries is available to the caller

### Requirement: The generated description MUST be inert at runtime

A generated type description MUST NOT be loaded, imported, or executed by the running
project, and MUST NOT introduce any runtime coupling between components that do not already
depend on one another. Deleting the description MUST change no runtime behavior.

#### Scenario: Description does not couple applications

- **WHEN** a description is generated for a project whose applications resolve each other
  only by identifier
- **AND** the project is then started and exercised
- **THEN** no application imports another application's modules at runtime

#### Scenario: Deleting the description is behavior-preserving

- **WHEN** a generated description is removed and the project is started
- **THEN** the project behaves exactly as it did with the description present

### Requirement: Generation MUST be deterministic

Describing the same project twice without changing it MUST produce byte-identical output.
Entries MUST be emitted in canonical identifier order so that unrelated changes to
declaration or load order do not perturb the output.

#### Scenario: Repeated generation is stable

- **WHEN** the same unchanged project is described twice
- **THEN** the two outputs are byte-identical

#### Scenario: Declaration order does not affect output

- **WHEN** two projects register identical components in different declaration orders
- **THEN** their descriptions are byte-identical

### Requirement: Verification MUST detect staleness without rewriting

The system MUST offer a verification mode that regenerates the description, compares it to
the stored one, and reports whether they match, without modifying the stored description.
Verification MUST report a mismatch when the project has gained, lost, or changed the type
of any component, and MUST report a match otherwise.

#### Scenario: Stored description is current

- **WHEN** verification runs against a project whose stored description was generated from
  its present state
- **THEN** verification reports a match
- **AND** the stored description is unmodified

#### Scenario: A component was added since generation

- **WHEN** a component is registered that the stored description does not contain
- **AND** verification runs
- **THEN** verification reports a mismatch identifying the missing identifier
- **AND** the stored description is unmodified

#### Scenario: Missing description

- **WHEN** verification runs and no stored description exists
- **THEN** verification reports a mismatch rather than succeeding silently

### Requirement: A generated description MUST be diagnostic-free under the declared checker set

A generated type description MUST produce no diagnostics when read by every type checker
in the project's declared conformance set, in every emission mode the generator offers.
Where a description deliberately deviates from a rule a checker enforces, the description
itself MUST carry the suppression, placed so that the checker honors it — a consumer MUST
NOT need to configure their checker, suppress anything on their side, or avoid a checker
in the set to use an emitted description cleanly.

Conformance MUST be verified against every emission mode, not asserted from the
generator's output text alone: a description generated in each mode is read by each
checker in the set, and any diagnostic on valid consuming code is a verification
failure.

#### Scenario: Every emission mode is verified against every checker

- **WHEN** conformance verification runs for the project
- **THEN** a description in each emission mode is checked by every type checker in the
  declared conformance set, against consuming code that is valid under that mode
- **AND** verification fails if any checker reports any diagnostic

#### Scenario: A suppression the checker does not honor is a failure, not a ship

- **WHEN** an emitted description carries an internal suppression placed where a checker
  in the declared set does not honor it, so that checker reports a diagnostic
- **THEN** verification fails before the description reaches a consumer

#### Scenario: Checker evolution is detected rather than inherited by consumers

- **WHEN** a checker in the declared set changes where or how it reports a diagnostic,
  such that a previously clean description no longer verifies
- **THEN** verification fails on the project's side
- **AND** the failure identifies the emission mode and checker that produced the
  diagnostic

### Requirement: Emission beyond the supported scale MUST be reported, not silent

The generator MUST report to the operator whenever the identifier-narrowed
description is produced for a registry larger than the scale the declared checker
set is known to support: the entry count, the documented threshold, and the
supported alternative surface. Generation MUST still produce the description — the
report informs a decision, it does not make one — and generation below the threshold
MUST remain silent on this subject.

#### Scenario: Past the threshold, the operator is told

- **WHEN** the identifier-narrowed description is generated for a registry whose
  entry count exceeds the documented threshold
- **THEN** the description is still written
- **AND** the report names the entry count, the threshold, and the alternative
  surface a larger registry should rely on

#### Scenario: Below the threshold, nothing changes

- **WHEN** the identifier-narrowed description is generated for a registry within
  the documented threshold
- **THEN** no scale report is produced
- **AND** the emitted description is byte-identical to what the generator produced
  before this requirement existed
