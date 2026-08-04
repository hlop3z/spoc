# Object Identity

## RENAMED Requirements

- FROM: `### Requirement: Validation rejects, never normalizes`
- TO: `### Requirement: Stated names verbatim, derived names converted`

## MODIFIED Requirements

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

Conversion applies only to this derivation step. Lookup remains exact: resolving an
identifier MUST NOT convert the string being resolved, so a non-canonical spelling of a
registered identifier MUST fail to resolve.

#### Scenario: Explicit non-conforming name rejected

- **WHEN** an object is registered with the explicit name `MyService`
- **THEN** registration fails with an error identifying the `name` segment and the value `MyService`
- **AND** no registration record is created

#### Scenario: Derived name converted from conventional class casing

- **WHEN** a class named `UserAccount` is registered without an explicit name
- **THEN** it is registered under the object_name `user_account`

#### Scenario: Derived name that cannot conform still fails

- **WHEN** a class whose intrinsic name begins with a digit is registered without an
  explicit name
- **THEN** registration fails with an error naming the segment and the offending value

#### Scenario: Lookup is never converted

- **WHEN** `models:blog.UserAccount` is resolved and `models:blog.user_account` is registered
- **THEN** resolution fails — the registered identifier is the only canonical form
