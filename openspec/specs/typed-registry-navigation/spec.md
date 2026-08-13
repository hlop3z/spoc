# Typed Registry Navigation

## Purpose

The identity grammar is `kind:namespace.object_name`. Reaching a component by that
string is one lookup; reaching it by walking those same three facets as members is
the same lookup, spelled so a type checker can describe every step. That spelling is
why this capability exists separately from resolution: a description built from
per-identifier narrowing stops being answerable as a registry grows, while one built
from members stays flat at any size. The surface is derived from the registry rather
than declared beside it, so the two cannot disagree, and it is a pure lookup that
never runs what it returns.

## Requirements

### Requirement: Navigation MUST expose every registered component along the identity grammar's segments

The system MUST provide a navigation surface over the registry whose steps are the
identity grammar's facets in order — kind, then namespace, then object name — such
that every registered component is reachable by exactly one path, and no path exists
for a component that is not registered. The surface MUST be derived from the
registry rather than separately declared, so the two cannot disagree and no
component is ever stated twice.

#### Scenario: Every registered component is reachable

- **WHEN** a project registers components across several kinds and namespaces
- **THEN** each component is reachable by navigating its kind, namespace, and object
  name
- **AND** no other path to it exists

#### Scenario: The path is the identifier, respelled

- **WHEN** a component with canonical identifier `kind:namespace.object_name` is
  registered
- **THEN** navigating the segments `kind`, `namespace`, `object_name` reaches it
- **AND** no segment name differs from the identifier's facets beyond the documented
  reserved-word escape

#### Scenario: Nothing is declared twice

- **WHEN** a component is registered through any registration path
- **THEN** it is navigable without any additional declaration, annotation, or
  registration step

### Requirement: Navigation MUST be a pure lookup yielding what identifier resolution yields

Navigating to a component MUST yield the same registry record that resolving its
canonical identifier yields — the identical record, not a copy or wrapper — and MUST
NOT invoke, construct, or otherwise execute the registered object. Navigation MUST
observe the same read-consistency rules as identifier resolution, including during
lifecycle transitions.

#### Scenario: The same record comes back

- **WHEN** one component is reached both by navigation and by resolving its
  canonical identifier
- **THEN** the two yield the identical record

#### Scenario: A callable component is not invoked

- **WHEN** a callable component is reached by navigation
- **THEN** the callable is returned uninvoked
- **AND** no effect of calling it is observed

### Requirement: A failed navigation step MUST name the segment and its candidates

Navigating to a segment that does not exist MUST fail at that step, naming the
segment that could not match and the candidates available at that step — the same
precision identifier resolution provides. Adding navigation MUST NOT coarsen any
failure a consumer could previously observe.

#### Scenario: Unknown object name

- **WHEN** navigation reaches a valid kind and namespace but names an object that
  does not exist there
- **THEN** the failure names the object name and the candidates in that namespace

#### Scenario: Unknown kind

- **WHEN** navigation names a kind the project does not declare
- **THEN** the failure names the kind and the declared kind set

### Requirement: A reserved-word segment MUST remain navigable through a deterministic escape

A grammar segment whose name is a reserved word in the host language MUST remain
navigable through a single, documented, deterministic escape spelling, applied
identically at the runtime surface and in the static description. The component's
canonical identifier MUST NOT change: the escape is a property of the member
spelling only.

#### Scenario: A kind named for a reserved word

- **WHEN** a project declares a kind whose name is a host-language reserved word
- **THEN** its components are navigable through the documented escape spelling
- **AND** their canonical identifiers carry the unescaped name

### Requirement: The static description of navigation MUST give member-level answers at any registry size

The generated type description MUST describe the navigation surface as nested typed
members, such that a valid path yields the component's concrete static type, an
invalid path is a static error naming the failing member, and both hold — within the
declared checker set and the conformance gate — regardless of how many components
the project registers. The description MUST derive from the same source as the rest
of the generated description and be covered by the same determinism, staleness, and
diagnostic-free requirements.

#### Scenario: A valid path yields the concrete type

- **WHEN** a consumer navigates a declared path in code read by a checker from the
  declared set
- **THEN** the checker reports the component's concrete static type, consistent with
  its shape

#### Scenario: An invalid member is a static error at that member

- **WHEN** a consumer writes a path whose final segment is not declared
- **THEN** every checker in the declared set reports an error naming that member
- **AND** the error does not enumerate the project's other components wholesale

#### Scenario: Scale does not change the outcome

- **WHEN** a project registers tens of thousands of components and its description
  is generated
- **THEN** conformance verification completes and passes under every checker in the
  declared set
