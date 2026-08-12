## ADDED Requirements

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

#### Scenario: Every registered component appears

- **WHEN** a project registering components across several kinds and namespaces is described
- **THEN** the description contains exactly one entry per registered canonical identifier
- **AND** contains no entry for any identifier that is not registered

#### Scenario: Components registered from configuration appear

- **WHEN** a project registers components through configuration rather than through module
  discovery
- **THEN** those components appear in the description on equal terms with discovered ones

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
