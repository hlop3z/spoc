# Public API Surface

## Purpose

A published artifact exposes many things a consumer can depend on: names reachable by
import, executable commands, plugin registrations, optional dependency groups,
configuration file schemas, and generated file contracts. This capability defines which of
those carry a stability promise, states the promise each tier makes, requires the promise
to be visible where the element is defined, and makes the declared surface verifiable
against the real one so the two cannot silently diverge.

## Requirements

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

### Requirement: Each tier states a distinct guarantee

The tiers MUST carry these guarantees and no others:

- `public` — MAY change incompatibly only in a major release, and only after completing
  the deprecation lifecycle.
- `provisional` — MAY change incompatibly in a minor release without a deprecation
  period, but MUST NOT change incompatibly in a patch release.
- `internal` — MAY change or be removed in any release, including a patch.

An element's tier MAY be raised at any time. Lowering an element's tier is itself an
incompatible change and MUST obey the guarantee of the tier being left.

#### Scenario: A public element survives a minor release

- **WHEN** a minor release is published
- **THEN** every element that was `public` in the prior release is still present and
  compatible

#### Scenario: A provisional element may break in a minor release

- **WHEN** a `provisional` element changes incompatibly in a minor release
- **THEN** the release is conformant, and no deprecation period was required

#### Scenario: Raising a tier is always allowed

- **WHEN** an `internal` element is promoted to `public` in a minor release
- **THEN** the release is conformant, because the promise strengthened

#### Scenario: Demotion obeys the tier being left

- **WHEN** a `public` element is demoted to `provisional`
- **THEN** the demotion is treated as an incompatible change to a `public` element and
  requires a major release preceded by the deprecation lifecycle

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

### Requirement: An element's withdrawal is visible where the element is defined

An element that has entered the withdrawal lifecycle MUST carry a mark that is readable
from the artifact itself, without executing it, in the same place its tier is readable.
The mark MUST name what replaces the element, or state that nothing does.

Withdrawal MUST NOT be expressed as a tier. A marked element keeps the tier it already
carried, and keeps every promise that tier makes, until the release that removes it —
because the entire purpose of the waiting period is that the promise stays in force while
consumers migrate. A surface description that reports withdrawal in place of the tier
MUST be treated as reporting the wrong thing, not a shorthand for it.

#### Scenario: A marked element keeps its tier

- **WHEN** a `public` element is marked for withdrawal
- **THEN** it is still reported as `public`, and its withdrawal is reported alongside that
  tier rather than instead of it

#### Scenario: A mark that names no replacement fails the check

- **WHEN** an element is marked for withdrawal and the mark neither names a replacement nor
  states that there is none
- **THEN** the check fails and names the element

#### Scenario: The withdrawal state is readable without executing the artifact

- **WHEN** the check is run against the working tree
- **THEN** it establishes each element's withdrawal state without executing the artifact,
  and reports as a gap any element whose state it could not read

### Requirement: Withdrawal is expressed one way, and any other way is reported

The artifact MUST express withdrawal through exactly one mechanism, so that the absence of
a mark means the element is not being withdrawn. A withdrawal signal produced by any other
means MUST be reported as a finding naming where it was produced.

An unrecognized expression of withdrawal MUST NOT be read as "not withdrawn". The failure
this prevents is silent and one-directional: an observer that does not recognize a mark
reports a fully compliant withdrawal as an undeprecated one, and — far worse — reports an
element with no lifecycle at all the same way, so the two become indistinguishable.

#### Scenario: An unsanctioned withdrawal signal is reported

- **WHEN** the artifact produces a withdrawal signal for an element by any means other than
  the single sanctioned mechanism
- **THEN** the check fails and names where the signal is produced

#### Scenario: The sanctioned mark is recognized wherever it appears

- **WHEN** an element carries the sanctioned mark
- **THEN** the check reports that element as withdrawn, whatever kind of element it is

### Requirement: The contract states what it does not cover

The contract MUST enumerate the aspects of otherwise-`public` elements that carry no
promise, so that consumers cannot infer a guarantee from silence. The exclusions MUST
include, at minimum:

- the human-readable text of error, log, and diagnostic messages — the error *types* and
  their hierarchy are `public`, their wording is not;
- the human-readable prose rendering of command output — the machine-readable rendering
  of the same command is `public`;
- the resolved versions of dependencies inside a named optional dependency group — the
  group's *name* and the capability it enables are `public`;
- internal attribute names and representations of otherwise-`public` types.

#### Scenario: Error type is promised, message text is not

- **WHEN** a release changes the wording of a `public` error's message without changing
  the error's type or position in the hierarchy
- **THEN** the change is compatible and requires no major release

#### Scenario: Machine output is promised, prose output is not

- **WHEN** a release changes a command's human-readable prose output while leaving its
  machine-readable output unchanged
- **THEN** the change is compatible

#### Scenario: A dependency group's name outlives its contents

- **WHEN** a release changes which dependencies a named optional group installs, while the
  group continues to enable the same capability
- **THEN** the change is compatible

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

### Requirement: A completed lifecycle is established from the published releases

Establishing that a removal completed the lifecycle MUST NOT rest on the immediately
preceding release alone. Comparing the working tree with one baseline can show that an
element was present and marked before it vanished, but cannot show *when* it was first
marked, which is what the waiting period is measured from.

The comparison MUST therefore establish, from the project's published releases, the
release in which the element was first marked, and MUST measure the waiting period in
minor releases. A patch release MUST NOT satisfy the waiting period. Both sides of the
comparison MUST be read by the same rules, so an element cannot be judged withdrawn at one
release and merely absent at another because they were observed differently.

#### Scenario: A removal marked only in the preceding release fails

- **WHEN** a `public` element is removed, and the release that first marked it is the
  release immediately preceding the removal
- **THEN** the check fails, naming the element and the release that marked it

#### Scenario: A patch release does not satisfy the waiting period

- **WHEN** an element is marked in a minor release, and only patch releases of that same
  minor line ship before it is removed
- **THEN** the check fails, because no full minor release shipped with the element still
  functional

#### Scenario: A completed lifecycle passes

- **WHEN** a `public` element is removed, it was first marked in an earlier minor release,
  and at least one full minor release shipped in between with the element still present
  and functional
- **THEN** the check reports the removal as compliant and does not fail on it

#### Scenario: A removal never marked at all fails

- **WHEN** a `public` element present in a published release is absent from the working
  tree and no published release carried a mark for it
- **THEN** the check fails and names the element

### Requirement: A coverage gap is reported, never silently passed

The check MUST state which kinds of element it is able to observe. Where a declared
element's kind is covered by no observer, the check MUST report it as unverifiable rather
than infer anything about it, and MUST NOT fail on it — a gap in coverage is not a
divergence.

An unobserved kind MUST NOT be reported as absent. Reporting "nobody looked" as "it is
gone" would make the check untrustworthy in exactly the direction that matters.

#### Scenario: An unobserved kind is reported

- **WHEN** the contract declares an element whose kind no observer covers
- **THEN** the check reports it as unverifiable, and its outcome is not a failure

#### Scenario: An unobserved kind is never mistaken for a removal

- **WHEN** an element's kind is not covered by any observer and the element is not among
  the observed elements
- **THEN** the check reports it as unverifiable and not as absent

#### Scenario: Gaps are visible in the result

- **WHEN** the check completes and any declared element was unverifiable
- **THEN** the count of unverifiable elements appears in its output, so a passing run
  never implies coverage it did not have

### Requirement: An undeterminable withdrawal history is reported, never assumed satisfied

The comparison MUST report an element's withdrawal history as undetermined whenever it
cannot establish it, and MUST NOT treat the removal as justified. A history is
undeterminable when the published releases cannot be reached, or when the mark could not
be read at some release.

This extends the requirement above that a coverage gap is reported rather than silently
passed, and it points the same direction: "nobody could tell" MUST NOT be reported as
"the lifecycle was completed". A comparison whose history was undeterminable MUST NOT
present a passing outcome as though the history had been checked.

#### Scenario: Unreachable release history is reported

- **WHEN** the comparison cannot reach the project's published releases
- **THEN** it reports that the withdrawal history could not be established, and its outcome
  is not a pass

#### Scenario: An undeterminable history is not a completed lifecycle

- **WHEN** an element is removed and the comparison cannot establish when it was first
  marked
- **THEN** it reports the element as undetermined rather than as compliant

#### Scenario: Undetermined elements are visible in the result

- **WHEN** the comparison completes and any element's withdrawal history was undeterminable
- **THEN** the count of undetermined elements appears in its output, so a run never implies
  a check it did not perform

### Requirement: Reaching an internal element is not a promotion

Reachability MUST NOT confer stability. An `internal` element that is technically
importable, invocable, or otherwise accessible remains `internal` regardless of how it is
reached or how many consumers reach it.

Where an `internal` element is genuinely required by a legitimate extension use case, the
resolution MUST be to expose an element at a `public` or `provisional` location — never to
leave the consumer depending on the `internal` path.

#### Scenario: Accessibility does not imply stability

- **WHEN** a consumer reaches an `internal` element through a path that the artifact does
  not prevent
- **THEN** the element remains `internal` and may still change in a patch release

#### Scenario: A real extension need is met by promotion

- **WHEN** an extension use case is found to require an `internal` element
- **THEN** an element covering that use case is exposed at a `public` or `provisional`
  location, and the use case no longer depends on the `internal` path
