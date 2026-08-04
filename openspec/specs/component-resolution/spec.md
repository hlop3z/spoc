# Component Resolution

## Purpose

Resolution turns a canonical identifier into its registry record — a pure
lookup that never executes what it returns, and whose failures are precise:
each names the exact segment that didn't resolve and the candidates that
would have. A typo never falls through to undefined behavior.

## Requirements

### Requirement: Resolution by canonical identifier

The system MUST resolve a canonical identifier string (`kind:namespace.object_name`) to
the corresponding registry record. Resolution MUST proceed segment by segment in the
fixed order kind → namespace → object_name.

#### Scenario: Successful resolution

- **WHEN** `model:blog.post` is resolved and a component with that identifier is registered
- **THEN** the corresponding registry record is returned

### Requirement: Failures name the failing segment

A failed resolution MUST raise an error — never return an empty result — and the error
MUST name the specific segment that failed to resolve, its value, and the candidates
that were valid at that step. A typo MUST NOT fall through to undefined behavior.

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

### Requirement: Resolution never executes

Resolution MUST be a pure lookup: it MUST NOT call, construct, or otherwise execute the
resolved object, and MUST NOT trigger side effects beyond the lookup itself. Invocation
is the caller's responsibility and is outside this capability.

#### Scenario: Lookup without invocation

- **WHEN** an identifier bound to a callable object is resolved
- **THEN** the callable is returned unexecuted

### Requirement: No operation segment

The resolution grammar MUST NOT accept an operation suffix (a fourth segment); an
identifier with more segments than `kind:namespace.object_name` MUST be rejected as
malformed.

#### Scenario: Operation suffix rejected

- **WHEN** `model:blog.post.create` is resolved
- **THEN** an error is raised describing the expected three-segment grammar
