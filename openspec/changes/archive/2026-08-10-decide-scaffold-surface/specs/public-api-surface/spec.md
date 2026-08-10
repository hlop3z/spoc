## ADDED Requirements

### Requirement: Exposure from a published namespace is justified

The contract derives an element's tier from how it is exposed. It MUST also constrain the
exposure itself, so that a published namespace cannot grow without any rule being broken.

An element MAY be exposed from a published namespace only when a consumer outside the
artifact must reference it by name to do something the artifact offers. The admissible
reasons MUST be limited to:

- an operation the consumer invokes;
- a contract the consumer implements or substitutes;
- a condition the consumer distinguishes in order to respond to it differently;
- a value the consumer supplies, reads, or compares against.

An element that exists so the artifact can compose its own parts MUST NOT be exposed from
a published namespace, however widely it is used within the artifact. Being needed by
several inner units is not one of the admissible reasons — it is evidence of internal
structure, which the contract does not promise.

Where an element is exposed, the reason MUST be determinable from the artifact rather than
recorded in a separate register, consistent with the tier rules requiring no external
list.

This requirement governs admission only. It does not alter how a tier follows from
exposure once an element has been admitted.

#### Scenario: An admissible element may be exposed

- **WHEN** an element is one a consumer must name to invoke an operation, implement a
  substitutable contract, distinguish a condition, or supply a value
- **THEN** exposing it from a published namespace is permitted, and its tier follows from
  the existing rules

#### Scenario: An internal composition detail is not exposed

- **WHEN** an element exists only so that the artifact's own units can be assembled
- **THEN** it is not exposed from a published namespace, and its tier is `internal`

#### Scenario: Internal reuse does not justify exposure

- **WHEN** an element is referenced by many of the artifact's inner units but by no
  consumer outside it
- **THEN** its breadth of internal use is not an admissible reason, and it remains
  `internal`

#### Scenario: An exposure with no admissible reason is a defect

- **WHEN** an element exposed from a published namespace matches none of the admissible
  reasons
- **THEN** the exposure is a defect in the change that introduced it, to be corrected by
  withdrawing the element from the published namespace

## MODIFIED Requirements

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

A `provisional` element MUST further state what would settle its tier: the question that
is open, or the condition under which it becomes `public` or is withdrawn. The tier is a
recorded judgement that the element is not yet settled, never the residue of a judgement
never made, and a consumer MUST be able to tell which by reading the element.

#### Scenario: Reading an element reveals its tier

- **WHEN** a consumer reads the definition or documentation of any `public` or
  `provisional` element
- **THEN** its tier is stated there

#### Scenario: Provisional carries an explicit warning

- **WHEN** a consumer reads a `provisional` element's documentation
- **THEN** it states that the element may change incompatibly in a minor release

#### Scenario: Provisional states what would settle it

- **WHEN** a consumer reads a `provisional` element's documentation
- **THEN** it states the open question or the condition under which the element's tier
  would settle, so the consumer can judge how likely the element is to change

#### Scenario: An unsettled tier is distinguishable from an undecided one

- **WHEN** an element carries the provisional notice without stating what would settle it
- **THEN** the contract is unsatisfied, because a tier that was never decided is
  indistinguishable from one deliberately left open

#### Scenario: No importable tier requires a second file

- **WHEN** a consumer determines the tier of any importable element, at any tier
- **THEN** the artifact itself is sufficient, and no separate declaration file is required
