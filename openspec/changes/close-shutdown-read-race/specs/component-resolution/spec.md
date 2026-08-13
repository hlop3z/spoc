## MODIFIED Requirements

### Requirement: Failures name the failing segment

A failed resolution MUST raise an error — never return an empty result — and the error
MUST name the specific segment that failed to resolve, its value, and the candidates
that were valid at that step. A typo MUST NOT fall through to undefined behavior.

A segment failure MUST mean the segment. When resolution cannot be served because the
framework is transitioning rather than because the identifier is absent, the failure MUST
be reported as that condition and MUST NOT be expressed as an unknown kind, namespace, or
object name. The two are different conditions with different remedies — one is corrected by
fixing the identifier, the other by ordering the call — and a caller MUST be able to tell
them apart by the error's type.

#### Scenario: Unknown kind

- **WHEN** `modle:blog.post` is resolved and `modle` is not a declared kind
- **THEN** an error is raised naming the kind segment, the value `modle`, and the declared kinds

#### Scenario: Unknown namespace

- **WHEN** `model:blogg.post` is resolved and no kind-`model` component exists in namespace `blogg`
- **THEN** an error is raised naming the namespace segment, the value `blogg`, and the
  namespaces that do have kind-`model` components

#### Scenario: Unknown object name

- **WHEN** `model:blog.pots` is resolved and namespace `blog` has kind-`model` components
  but none named `pots`
- **THEN** an error is raised naming the object_name segment and the value `pots`

#### Scenario: Malformed identifier

- **WHEN** a string that does not parse as `kind:namespace.object_name` is resolved
- **THEN** an error is raised describing the expected grammar and the received value

#### Scenario: An unavailable framework is not an unknown segment

- **WHEN** `model:blog.post` is registered, the framework is mid-transition, and an
  unrelated caller resolves it
- **THEN** the error states that the framework is transitioning, names no segment as
  unknown, and is a different type from every unknown-segment error

#### Scenario: The same identifier resolves once the framework settles

- **WHEN** an identifier that failed with the transitioning error is resolved again against
  a started framework with that component registered
- **THEN** it resolves successfully, confirming the earlier failure described the
  framework's state and not the identifier
