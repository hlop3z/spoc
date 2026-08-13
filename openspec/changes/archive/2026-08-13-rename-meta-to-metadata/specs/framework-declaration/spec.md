# Delta: framework-declaration

## MODIFIED Requirements

### Requirement: Each kind states its component metadata contract

Every declared kind MUST be able to state the contract for metadata carried by its
components. Where a kind states a contract, metadata supplied at registration MUST be
checked against it, and a violation MUST fail with an error naming the kind, the
component, and the way the metadata departs from the contract. Where a kind states no
contract, its components MUST carry no metadata beyond what the kernel itself records,
so there is no untyped channel available by default.

Every surface that accepts component metadata MUST name it `metadata` — the same word
the kind declaration and the registry record use. One concept carries one name across
declaration, registration, and the record; a registration surface that introduces a
second spelling for it is a defect.

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

#### Scenario: One name for the concept at every surface

- **WHEN** a component is registered with metadata through any registration surface —
  the low-level marker or a kind's registration handle
- **THEN** the surface accepts it under the name `metadata`, and the record exposes it
  under the same name
