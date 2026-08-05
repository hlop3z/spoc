# Framework Declaration — delta

## MODIFIED Requirements

### Requirement: Single declaration point

A framework MUST be declared as exactly one object carrying the closed kind set and,
for each kind, everything the kernel knows about it: its position in the inter-kind
dependency order, whether its modules are required or optional, and the metadata
contract its components carry. No other public surface SHALL accept a kind-set
declaration or any per-kind attribute, so a second, conflicting declaration point
cannot exist and no kind attribute can be stated away from the kind it describes.

Declaring the same kind more than once within one declaration MUST fail, naming the
duplicated kind. A later declaration never silently replaces an earlier one.

#### Scenario: Kinds are stated once

- **WHEN** a framework is declared with kinds `models` and `views`
- **THEN** that single declaration is the source of the registry's closed kind set and
  of module discovery, with no second kind list to keep in agreement

#### Scenario: Dependencies ride the same declaration

- **WHEN** the declaration states that `views` depends on `models`
- **THEN** modules of kind `models` are loaded and initialized before modules of kind
  `views` in every app, with no separate ordering declaration

#### Scenario: Per-kind attributes ride the same declaration

- **WHEN** the declaration states that `views` is optional and that `models` components
  carry a stated metadata contract
- **THEN** both attributes are read from that one declaration, with no parallel
  structure keyed by kind name holding either of them

#### Scenario: Duplicate kind declaration is refused

- **WHEN** a framework is declared naming the kind `models` twice, whatever the form of
  either declaration
- **THEN** construction fails with an error naming `models`, and no framework object is
  produced

### Requirement: Per-kind registration handles

The framework object MUST hand out a registration handle for any declared kind.
Requesting a handle for an undeclared kind MUST fail immediately, naming the unknown
kind and the declared set.

Marking an object that cannot carry the mark MUST fail with a kernel error naming the
object and the constraint it violates — never a raw language-level attribute failure
that leaves the author to infer the rule.

#### Scenario: Handle for a declared kind

- **WHEN** the author requests a registration handle for `models`
- **THEN** a handle is returned that registers objects under kind `models` in the
  framework's registry

#### Scenario: Handle for an undeclared kind

- **WHEN** the author requests a handle for `controllers` and the declared set is
  `models, views`
- **THEN** the request fails naming `controllers` and listing `models, views`

#### Scenario: Unmarkable object is refused with the constraint named

- **WHEN** a handle is applied to an object that cannot carry the registration mark
  (for example, an instance of a class that forbids new attributes)
- **THEN** the operation fails with a kernel error naming the object and stating the
  constraint, not a raw attribute error
