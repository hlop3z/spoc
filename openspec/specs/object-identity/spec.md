# Object Identity

## Purpose

Every object the kernel manages has exactly one canonical identifier —
`kind:namespace.object_name` — treated as a contract: validated at
registration and never inferred from the execution environment. A name the
author states is used verbatim; a name derived from the object's own name is
converted to the canonical casing first. This capability defines the grammar,
its validation semantics, and the closed kind set.

## Requirements

### Requirement: Single identifier grammar

Every registered object MUST be identified by exactly one canonical identifier of the
form `kind:namespace.object_name`, where `kind`, `namespace`, and `object_name` are each
non-empty and match `^[a-z][a-z0-9_]*$` (lowercase snake_case). No other identifier form
SHALL exist for a registered object.

Wherever the public surface exposes the segments individually — parsed identifiers,
record fields, error vocabulary — the third segment MUST be named `object_name`, the
same word the grammar uses, so there is no second vocabulary to translate.

#### Scenario: Well-formed identifier accepted

- **WHEN** an object is registered with kind `model`, namespace `blog`, and name `post`
- **THEN** its canonical identifier is `model:blog.post`

#### Scenario: One identifier per object

- **WHEN** a registered object's identity is queried through any part of the public API
- **THEN** every answer is the same canonical `kind:namespace.object_name` string

#### Scenario: Segment vocabulary is uniform

- **WHEN** an identifier is parsed through the public API and its segments are read
  individually
- **THEN** the third segment is exposed under the name `object_name`, matching the
  grammar and the error vocabulary

#### Scenario: Round-trip identity over the whole grammar

- **WHEN** any three conforming segments are composed into an identifier and that
  identifier is parsed back
- **THEN** the parsed segments equal the originals exactly — for every conforming
  input, not only named examples

#### Scenario: Rejection is complete over the whole input space

- **WHEN** any string that is not a well-formed `kind:namespace.object_name` — or any
  segment violating `^[a-z][a-z0-9_]*$` — is parsed or validated
- **THEN** it is refused with the grammar's error naming the offending part; no
  non-conforming input is ever accepted, converted, or partially parsed

### Requirement: Stated names verbatim, derived names converted

An identifier segment supplied **explicitly** MUST be used verbatim and validated: a
segment that violates the grammar MUST cause registration to fail with an error that
names the offending segment and its invalid value, and the system MUST NOT silently
transform it to make it conform.

A name **derived** from an object's own intrinsic name (rather than supplied
explicitly) MUST be converted to the canonical snake_case form before validation, so
that a name following the host language's conventional class casing yields the
conventional identifier segment without the author restating it. The derived value MUST
then be validated like any other: a derived name that does not conform even after
conversion MUST fail with the same error, never a guess or a partial match.

The failure MUST describe the path actually taken: a failure over a stated name says
the name was stated and used verbatim; a failure over a derived name says the name was
derived and names the intrinsic name it came from. Remediation advice MUST match that
path — it never tells the author of a derived-name failure that their stated name was
used verbatim.

Conversion applies only to this derivation step. Lookup remains exact: resolving an
identifier MUST NOT convert the string being resolved, so a non-canonical spelling of a
registered identifier MUST fail to resolve.

#### Scenario: Explicit non-conforming name rejected

- **WHEN** an object is registered with the explicit name `MyService`
- **THEN** registration fails with an error identifying the `object_name` segment and the value `MyService`
- **AND** no registration record is created

#### Scenario: Derived name converted from conventional class casing

- **WHEN** a class named `UserAccount` is registered without an explicit name
- **THEN** it is registered under the object_name `user_account`

#### Scenario: Derived name that cannot conform still fails

- **WHEN** a class whose intrinsic name begins with a digit is registered without an
  explicit name
- **THEN** registration fails with an error naming the segment and the offending value

#### Scenario: Derived-name failure names the derivation

- **WHEN** a name derived from an object's intrinsic name fails validation
- **THEN** the error states the name was derived, names the intrinsic name it came
  from, and its remediation advice does not describe the name as stated verbatim

#### Scenario: Lookup is never converted

- **WHEN** `models:blog.UserAccount` is resolved and `models:blog.user_account` is registered
- **THEN** resolution fails — the registered identifier is the only canonical form

### Requirement: Closed kind set

The set of valid kinds MUST be declared explicitly in the project's composition
configuration before any registration occurs. Registering an object under a kind not in
the declared set MUST fail with an error naming the unknown kind and listing the
declared kinds. Adding a kind MUST require changing the declared set — it MUST NOT
happen implicitly as a side effect of registration or lookup.

#### Scenario: Unknown kind rejected

- **WHEN** the declared kind set is {`model`, `view`} and an object is registered under kind `modle`
- **THEN** registration fails with an error naming `modle` and listing `model` and `view`

#### Scenario: Kind set fixed at composition time

- **WHEN** the application has started
- **THEN** no API exists to extend the kind set at runtime

### Requirement: Explicit identity for anonymous objects

An object that does not intrinsically carry a name (such as a bare instance) MUST be
registered with an explicitly supplied name. The system MUST NOT infer identity from the
execution environment (caller variable names, stack inspection, or similar), and MUST
NOT mutate the object being registered in order to derive its identity.

#### Scenario: Instance registered with explicit name

- **WHEN** an instance is registered with an explicit name `post_repository`
- **THEN** it is registered under that name

#### Scenario: Instance registered without a name

- **WHEN** an instance lacking an intrinsic name is registered without an explicit name
- **THEN** registration fails with an error stating that a name is required
