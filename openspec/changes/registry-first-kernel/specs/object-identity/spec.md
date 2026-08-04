# Object Identity

## ADDED Requirements

### Requirement: Single identifier grammar

Every registered object MUST be identified by exactly one canonical identifier of the
form `kind:namespace.object_name`, where `kind`, `namespace`, and `object_name` are each
non-empty and match `^[a-z][a-z0-9_]*$` (lowercase snake_case). No other identifier form
SHALL exist for a registered object.

#### Scenario: Well-formed identifier accepted

- **WHEN** an object is registered with kind `model`, namespace `blog`, and name `post`
- **THEN** its canonical identifier is `model:blog.post`

#### Scenario: One identifier per object

- **WHEN** a registered object's identity is queried through any part of the public API
- **THEN** every answer is the same canonical `kind:namespace.object_name` string

### Requirement: Validation rejects, never normalizes

Identifier segments MUST be validated at registration time. A segment that violates the
grammar MUST cause registration to fail with an error that names the offending segment
and its invalid value. The system MUST NOT silently transform (case-fold, restyle, or
otherwise rewrite) a segment to make it conform.

#### Scenario: Non-snake_case name rejected

- **WHEN** an object is registered whose name segment is `MyService`
- **THEN** registration fails with an error identifying the `name` segment and the value `MyService`
- **AND** no registration record is created

#### Scenario: No silent normalization

- **WHEN** an object is registered whose name segment would only be valid after case
  conversion
- **THEN** the system does not convert it and registration fails

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
