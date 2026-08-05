## MODIFIED Requirements

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
