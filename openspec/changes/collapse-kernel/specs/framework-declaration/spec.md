## MODIFIED Requirements

### Requirement: Single declaration point

A framework MUST be declared as exactly one object carrying the closed kind set and,
for each kind, everything the kernel knows about it: its position in the inter-kind
dependency order, whether its modules are required or optional, and the metadata
contract its components carry. No other public surface SHALL accept a kind-set
declaration or any per-kind attribute, so a second, conflicting declaration point
cannot exist and no kind attribute can be stated away from the kind it describes.

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

## ADDED Requirements

### Requirement: Each kind states whether its modules are required

Every declared kind MUST state whether modules of that kind are required or optional.
This attribute SHALL be settable per kind and MUST NOT be expressible as a single
framework-wide setting, so declaring a kind that only some apps implement does not
weaken the guarantee for every other kind. A kind that does not state the attribute
MUST default to required, so tolerating a missing module is always a deliberate act.

#### Scenario: Optional kind declared alongside required ones

- **WHEN** a framework declares `models` as required and `views` as optional
- **THEN** the requirement of `models` is unaffected by the optionality of `views`

#### Scenario: Unstated optionality defaults to required

- **WHEN** a kind is declared without stating optionality
- **THEN** modules of that kind are treated as required

### Requirement: Each kind states its component metadata contract

Every declared kind MUST be able to state the contract for metadata carried by its
components. Where a kind states a contract, metadata supplied at registration MUST be
checked against it, and a violation MUST fail with an error naming the kind, the
component, and the way the metadata departs from the contract. Where a kind states no
contract, its components MUST carry no metadata beyond what the kernel itself records,
so there is no untyped channel available by default.

#### Scenario: Metadata conforming to the declared contract

- **WHEN** a component of a kind that states a metadata contract is registered with
  metadata satisfying it
- **THEN** registration succeeds and the record carries that metadata

#### Scenario: Metadata violating the declared contract

- **WHEN** a component is registered with metadata that departs from its kind's stated
  contract
- **THEN** registration fails naming the kind, the component, and the departure
- **AND** the component is not registered

#### Scenario: No contract means no free-form channel

- **WHEN** a kind states no metadata contract and one of its components is registered
  with metadata
- **THEN** registration fails, because the kind declares no contract for it to satisfy
