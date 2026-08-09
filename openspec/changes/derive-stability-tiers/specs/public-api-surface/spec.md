## MODIFIED Requirements

### Requirement: Every surface element has exactly one tier

Every element of the published surface MUST be assigned exactly one stability tier from
the closed set `public`, `provisional`, `internal`. The surface comprises every element a
consumer can depend on without modifying the artifact: names reachable by import,
executable commands and their machine-readable output, plugin registrations, named
optional dependency groups, configuration file schemas, and the contract of files the
artifact generates.

No element SHALL be untiered. An element whose tier has not been decided MUST be treated
as `internal` — the absence of a promise is never read as a promise.

For an element reachable by import, the tier MUST be a consequence of how the element is
exposed and documented, determined by rules stated in this contract rather than by a
separate list. The rules MUST be total and MUST assign at most one tier, so that no
importable element depends on a declaration kept elsewhere:

- An element exposed only from an inner unit of the artifact, and not from a namespace the
  contract publishes for consumers, is `internal`.
- An element whose own documentation carries the provisional notice is `provisional`.
- Any other element exposed from a published namespace is `public`.

For an element **not** reachable by import, the tier MUST be declared explicitly, because
no such rule can observe it. The set of element kinds requiring explicit declaration MUST
be stated, so it is clear which elements the rules govern and which are declared.

#### Scenario: Every element resolves to a tier

- **WHEN** any element of the published surface is looked up in the contract
- **THEN** exactly one of `public`, `provisional`, or `internal` is returned

#### Scenario: An undeclared element is not public

- **WHEN** an element exists in the artifact but neither matches a stated rule nor appears
  in the explicit declarations
- **THEN** it is treated as `internal` and carries no stability promise

#### Scenario: Non-import surfaces are covered

- **WHEN** the contract is examined for an executable command, a plugin registration, a
  named optional dependency group, or a configuration file schema
- **THEN** each has a tier, on the same terms as an importable name

#### Scenario: Exposure decides the tier of an importable element

- **WHEN** an importable element is exposed only from an inner unit of the artifact
- **THEN** its tier is `internal`, and it becomes `public` if and only if it is later
  exposed from a published namespace

#### Scenario: The provisional notice decides the tier

- **WHEN** an element exposed from a published namespace carries the provisional notice in
  its documentation
- **THEN** its tier is `provisional`, and removing that notice makes it `public`

#### Scenario: The rules need no separate list

- **WHEN** an importable element's tier is determined
- **THEN** it is determined from the artifact alone, with no list of names maintained
  outside the artifact consulted

### Requirement: The tier is visible where the element is defined

An element's tier MUST be discoverable at its point of definition, not only in a separate
document. A consumer reading the element MUST be able to see its tier without consulting
another file.

For an element reachable by import this MUST hold for every tier, not only for the tier
that carries an explicit notice: because the tier follows from how the element is exposed
and documented, reading the element and the namespace that exposes it is sufficient to
determine it.

A `provisional` element MUST additionally be marked such that opting into it is
deliberate — its documentation MUST state that it may break in a minor release.

#### Scenario: Reading an element reveals its tier

- **WHEN** a consumer reads the definition or documentation of any `public` or
  `provisional` element
- **THEN** its tier is stated there

#### Scenario: Provisional carries an explicit warning

- **WHEN** a consumer reads a `provisional` element's documentation
- **THEN** it states that the element may change incompatibly in a minor release

#### Scenario: No importable tier requires a second file

- **WHEN** a consumer determines the tier of any importable element, at any tier
- **THEN** the artifact itself is sufficient, and no separate declaration file is required

### Requirement: The declared surface is verifiable against the real surface

The project MUST provide a check that establishes the tier of every surface element and
reports any inconsistency as a failure. The check MUST be runnable as part of the
project's standard validation, without publishing a release.

For elements governed by the stated rules, the check MUST verify that the rules resolve
cleanly: every such element MUST resolve to exactly one tier, and an element that matches
no rule or more than one MUST fail the check, naming the element. Because the rules read
the artifact directly, there is no separate declaration for them to diverge from, and the
check MUST NOT invent one.

For elements whose tier is declared explicitly, divergence in either direction MUST fail:
an element declared but absent from the artifact, and an element exposed by the artifact
whose kind requires declaration but which is not declared.

#### Scenario: An ambiguous element fails the check

- **WHEN** an element matches no stated rule, or matches rules assigning different tiers
- **THEN** the check fails and names the element

#### Scenario: An undeclared non-import element fails the check

- **WHEN** an element of a kind requiring explicit declaration is added to the published
  surface without being declared
- **THEN** the check fails and names the undeclared element

#### Scenario: A declared but missing element fails the check

- **WHEN** an explicit declaration names an element that the artifact no longer exposes
- **THEN** the check fails and names the missing element

#### Scenario: A conformant surface passes

- **WHEN** every governed element resolves to one tier and every declared element is
  present
- **THEN** the check passes

#### Scenario: The check needs no release

- **WHEN** the check is run against the working tree
- **THEN** it completes without publishing or fetching a released artifact
