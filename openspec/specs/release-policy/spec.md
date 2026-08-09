# Release Policy

## Purpose

A stability tier is only worth as much as the release process that honours it. This
capability binds version numbers to the guarantees in the public API surface: what each
version increment asserts, how an element is withdrawn without breaking consumers
silently, what each release must record, and the criteria that must hold before the
project declares itself stable. It defines *when* the surface may change; the surface
capability defines *what* may change.

## Requirements

### Requirement: Version increments assert compatibility

The project MUST version releases under Semantic Versioning, and each increment MUST
assert exactly this about the published surface:

- **patch** — no element of any tier above `internal` changed incompatibly.
- **minor** — no `public` element changed incompatibly; `provisional` elements MAY have.
  Elements MAY have been added at any tier.
- **major** — `public` elements MAY have changed incompatibly, each having completed the
  deprecation lifecycle.

A release MUST NOT be published under an increment whose assertion it violates. Where a
change's compatibility is genuinely ambiguous, the project MUST choose the larger
increment.

The assertion MUST be checkable rather than asserted by hand. The project MUST provide a
check that compares the surface of the working tree against the surface of the previously
released artifact and reports every difference it finds, classified as compatible or
incompatible. The check MUST run as part of standard validation, before a release is
published, and MUST fail when a difference is incompatible with the increment being
claimed.

The check MUST report an element newly exposed at a `public` or `provisional` tier, not
only elements removed or altered. Growth of the surface is a reviewable event: an element
gains a stability promise the moment it is exposed, and that MUST be visible in the change
that exposes it.

#### Scenario: A compatible addition is a minor release

- **WHEN** a release adds new elements and changes no existing element incompatibly
- **THEN** it is published as a minor release

#### Scenario: An incompatible public change forces a major release

- **WHEN** a change would alter a `public` element incompatibly
- **THEN** the change MUST NOT ship in a patch or minor release

#### Scenario: Ambiguity resolves upward

- **WHEN** it cannot be established whether a change is compatible
- **THEN** the larger version increment is chosen

#### Scenario: A removed public element is caught before release

- **WHEN** a `public` element present in the previous release is absent from the working
  tree, and no major increment is being claimed
- **THEN** the check fails and names the removed element

#### Scenario: Newly exposed surface is reported

- **WHEN** an element is exposed at `public` or `provisional` that was not exposed in the
  previous release
- **THEN** the check reports it as an addition, naming the element and its tier

#### Scenario: An unchanged surface passes

- **WHEN** the working tree exposes the same elements, compatibly, as the previous release
- **THEN** the check passes and reports no difference

### Requirement: The pre-stable allowance is explicit and ends at 1.0

The project MUST publish a single, explicit allowance for the pre-stable period: before
the first stable major release, a `public` element MAY change incompatibly in a minor
release without completing the deprecation lifecycle. The allowance MUST be stated
wherever the policy is published, and it MUST end the moment the first stable major
release is cut — after which incompatible changes to `public` elements obey the full
policy without exception.

The allowance MUST NOT be extended by re-releasing under a pre-stable version once the
stability criteria are met.

#### Scenario: A pre-stable minor may break a public element

- **WHEN** a `public` element changes incompatibly before the first stable major release
- **THEN** the change may ship in a minor release, and the release records it as breaking

#### Scenario: The allowance is spent at the stable release

- **WHEN** the first stable major release has been published
- **THEN** no subsequent minor or patch release changes a `public` element incompatibly

#### Scenario: The policy is published with its allowance

- **WHEN** a consumer reads the published policy while the project is pre-stable
- **THEN** the allowance and its end condition are stated there

### Requirement: A public element is withdrawn through a deprecation lifecycle

Once the pre-stable allowance has ended, a `public` element MUST NOT be removed or changed
incompatibly until it has completed a deprecation lifecycle:

1. The element is marked deprecated, and its documentation names its replacement, or
   states plainly that there is none.
2. Using the element produces a runtime deprecation signal that names the element and its
   replacement, and that a consumer can suppress or escalate.
3. The element remains present and functional for at least one full minor release after
   the release that first marked it deprecated.
4. Only then MAY a major release remove it.

An element MUST NOT be removed in the same release that first deprecated it. Nothing MUST
be removed without a deprecation signal having been available.

The lifecycle MUST be enforced by the same comparison that checks compatibility: a
`public` element that has disappeared relative to the previous release MUST fail unless
the record shows it was marked deprecated in an earlier release. Detection MUST NOT depend
on a reviewer remembering the element existed.

#### Scenario: Deprecation precedes removal by at least one minor release

- **WHEN** a `public` element is removed in a major release
- **THEN** it was marked deprecated in an earlier release, and at least one full minor
  release shipped in between with the element still functional

#### Scenario: Using a deprecated element signals at runtime

- **WHEN** a consumer uses an element that has been marked deprecated
- **THEN** a deprecation signal is produced that names the element and its replacement

#### Scenario: Deprecation and removal never share a release

- **WHEN** a release marks an element deprecated
- **THEN** that same release still provides the element in working form

#### Scenario: A deprecation with no replacement still states so

- **WHEN** an element is deprecated and nothing replaces it
- **THEN** its documentation states that there is no replacement, rather than omitting the
  question

#### Scenario: An undeprecated removal is refused

- **WHEN** a `public` element present in the previous release is absent from the working
  tree and was never marked deprecated
- **THEN** the check fails and names the element, whatever increment is being claimed

### Requirement: Every release records its surface changes

Every release MUST record, in the project's published history, each change to the surface
that a consumer could observe: elements added, elements deprecated, elements removed, and
every incompatible change with the tier of the element it affected.

A release that changes a `public` element incompatibly MUST record it as breaking, in
terms of what a consumer must do, not only what the project did.

#### Scenario: A breaking change is recorded as breaking

- **WHEN** a release changes a `public` element incompatibly
- **THEN** the published history records it as breaking and states what a consumer must
  change

#### Scenario: Deprecations are recorded when marked, not when removed

- **WHEN** a release marks an element deprecated
- **THEN** that release's history entry records the deprecation, rather than deferring the
  record to the release that removes the element

#### Scenario: Tier transitions are recorded

- **WHEN** a release moves an element between tiers
- **THEN** the published history names the element, its old tier, and its new tier

### Requirement: The stable release has stated, checkable criteria

The project MUST publish the criteria that MUST all hold before the first stable major
release is cut, and each criterion MUST be objectively determinable rather than a matter
of judgement. The criteria MUST include, at minimum:

- every element of the published surface has a tier, and the surface verification check
  passes;
- no element that the project intends to be `public` at the stable release is still
  `provisional`;
- the deprecation lifecycle is implemented and exercised, not merely documented.

The stable release MUST NOT be cut while any published criterion is unmet, and the
criteria MUST NOT be weakened in the same change that cuts the release.

#### Scenario: An unmet criterion blocks the stable release

- **WHEN** any published stable-release criterion does not hold
- **THEN** the first stable major release is not cut

#### Scenario: Criteria are determinable without judgement

- **WHEN** each published criterion is evaluated
- **THEN** it yields a definite met-or-unmet answer

#### Scenario: Criteria are not weakened to reach the release

- **WHEN** a change both alters the stable-release criteria and cuts the stable release
- **THEN** the change is rejected

### Requirement: The declared maturity matches the policy in force

The maturity the project declares in its distribution metadata MUST correspond to the
policy actually in force. While the pre-stable allowance is available, the metadata MUST
NOT declare a stable maturity; once the first stable major release is published, the
metadata MUST declare a stable maturity.

#### Scenario: Pre-stable metadata does not claim stability

- **WHEN** the project is published while the pre-stable allowance is still available
- **THEN** its distribution metadata declares a pre-stable maturity

#### Scenario: The stable release updates the declared maturity

- **WHEN** the first stable major release is published
- **THEN** its distribution metadata declares a stable maturity in the same release
