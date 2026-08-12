## ADDED Requirements

### Requirement: The registry MUST have one described projection as data

The project MUST publish exactly one projection of a booted registry as data, and every
surface that describes the registry MUST derive from it rather than from a private
structure of its own. The projection MUST describe, for every registered component, its
canonical identifier and the three facets that compose it, where the registered object is
defined, and the object's shape; and MUST describe the project's declared kind set. Two
descriptions of one registry cannot then disagree, because there is only one.

The projection MUST NOT carry anything that requires the consuming system to be written in
the same language as the framework, so that the description outlives any one implementation
of it.

#### Scenario: Every component appears once

- **WHEN** a project with components across several kinds and namespaces is projected
- **THEN** the document contains exactly one entry per registered component, and the entry
  states the component's identifier, kind, namespace, object name, defining location, and
  shape

#### Scenario: The declared kind set is part of the description

- **WHEN** a project declaring kinds `models` and `views` is projected
- **THEN** the document states both kinds, including any kind for which no component was
  registered

#### Scenario: One projection, many surfaces

- **WHEN** any surface of this project describes registry contents to a consumer outside
  the process
- **THEN** it derives that description from the projection, and no second structure
  describing the same components exists

### Requirement: The projection MUST validate against a published schema

The projection MUST have a published schema, expressed in a standard schema language, that
a consumer can obtain and validate a document against without executing project code or
reading its source. The schema MUST be published with the project rather than described
only in prose, and every document the project emits MUST validate against it.

The document MUST state the version of the projection format itself, independently of the
framework's release version, so a document found separately from the tool that produced it
still identifies what it is.

#### Scenario: An emitted document validates

- **WHEN** any projection this project emits is validated against the published schema
- **THEN** validation succeeds

#### Scenario: The format version is in the document

- **WHEN** a consumer reads a projection without knowing which release produced it
- **THEN** the document states the projection format's version, and that version is not the
  framework's release version

#### Scenario: A malformed document is detectable

- **WHEN** a document is missing a required field or uses a value outside a stated
  vocabulary
- **THEN** validation against the published schema fails, identifying the offending part

### Requirement: Projection MUST NOT require initializing the project

Producing a projection MUST require only discovery — configuration, app loading, and
component registration — and MUST NOT require lifecycle initialization or startup hooks to
run. Describing what a project registers therefore succeeds in environments where starting
it would not, such as a checkout with no access to the services its hooks contact.

The projection MUST state that it describes the registry as of the completion of discovery,
including anything registered by ready callbacks, and MUST NOT be presented as describing
components a startup hook might register afterwards.

#### Scenario: A project whose startup would fail is still describable

- **WHEN** a project is projected whose startup hook would raise
- **THEN** the projection is produced successfully and describes every registered component

#### Scenario: Ready-callback registrations are included

- **WHEN** a project registers components from a ready callback
- **THEN** those components appear in the projection, because ready callbacks complete
  within discovery

#### Scenario: A discovery failure is still a failure

- **WHEN** a project is projected whose configuration is invalid or whose app module cannot
  be imported
- **THEN** projection fails with the framework's own error for that condition, unchanged

### Requirement: Projection order MUST be canonical identifier order

Entries MUST be emitted in canonical identifier order, so that two projections of one
registry are identical and a difference between two projections reflects a difference in
the registry rather than in declaration order, load order, or filesystem layout. This
ordering is a property of the projection itself and MUST NOT be stated only by reference to
another surface that happens to share it.

No value in the document may vary between two runs over one unchanged registry. In
particular, a component's stated location MUST NOT be derived from anything carrying a
process-specific value, such as an object's memory address.

#### Scenario: Two projections of one registry are identical

- **WHEN** one unchanged project is projected twice
- **THEN** the two documents are byte-identical

#### Scenario: Reordering declarations does not reorder the projection

- **WHEN** a project's installed-app list is reordered without changing what is registered
- **THEN** the projection is unchanged

#### Scenario: A registered instance is located stably

- **WHEN** a project registering an object that carries no definition site of its own is
  projected twice
- **THEN** the two documents state the same location for it

### Requirement: The projection MUST be available as a library result and as a command

The projection MUST be obtainable both by calling the project's library and by running a
command, and both MUST describe the same registry with the same content and the same
ordering. The command MUST be a thin adapter over the library operation, so no behaviour
exists only when invoked through a terminal.

#### Scenario: Command and library agree

- **WHEN** one project is projected through the command and through the library
- **THEN** both yield the same document

#### Scenario: The command writes to standard output

- **WHEN** the command is run against a valid project
- **THEN** the document is written to standard output, suitable for piping to another tool
