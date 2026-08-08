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

#### Scenario: Every element resolves to a tier

- **WHEN** any element of the published surface is looked up in the contract
- **THEN** exactly one of `public`, `provisional`, or `internal` is returned

#### Scenario: An undeclared element is not public

- **WHEN** an element exists in the artifact but appears nowhere in the contract
- **THEN** it is treated as `internal` and carries no stability promise

#### Scenario: Non-import surfaces are covered

- **WHEN** the contract is examined for an executable command, a plugin registration, a
  named optional dependency group, or a configuration file schema
- **THEN** each has a tier, on the same terms as an importable name

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

A `provisional` element MUST additionally be marked such that opting into it is
deliberate — its documentation MUST state that it may break in a minor release.

#### Scenario: Reading an element reveals its tier

- **WHEN** a consumer reads the definition or documentation of any `public` or
  `provisional` element
- **THEN** its tier is stated there

#### Scenario: Provisional carries an explicit warning

- **WHEN** a consumer reads a `provisional` element's documentation
- **THEN** it states that the element may change incompatibly in a minor release

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

The project MUST provide a check that compares the surface the contract declares against
the surface the artifact actually exposes, and reports any divergence as a failure. The
check MUST be runnable as part of the project's standard validation, without publishing a
release.

Divergence in either direction MUST fail: an element declared in the contract but absent
from the artifact, and an element exposed by the artifact but absent from the contract.

#### Scenario: An undeclared new element fails the check

- **WHEN** a new element is added to the published surface without being added to the
  contract
- **THEN** the check fails and names the undeclared element

#### Scenario: A declared but missing element fails the check

- **WHEN** the contract declares an element that the artifact no longer exposes
- **THEN** the check fails and names the missing element

#### Scenario: A conformant surface passes

- **WHEN** the declared contract and the exposed surface agree
- **THEN** the check passes

#### Scenario: The check needs no release

- **WHEN** the check is run against the working tree
- **THEN** it completes without publishing or fetching a released artifact

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
