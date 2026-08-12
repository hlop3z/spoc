## MODIFIED Requirements

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
