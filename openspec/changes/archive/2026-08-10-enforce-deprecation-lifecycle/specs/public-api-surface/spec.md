## ADDED Requirements

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

### Requirement: An undeterminable withdrawal history is reported, never assumed satisfied

The comparison MUST report an element's withdrawal history as undetermined whenever it
cannot establish it, and MUST NOT treat the removal as justified. A history is
undeterminable when the published releases cannot be reached, or when the mark could not
be read at some release.

This extends the existing rule that a coverage gap is reported rather than silently
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
