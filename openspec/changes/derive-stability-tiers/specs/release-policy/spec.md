## MODIFIED Requirements

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
