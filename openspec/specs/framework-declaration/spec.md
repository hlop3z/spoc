# Framework Declaration

## Purpose

A framework is declared exactly once, on one object: its closed kind set, the
inter-kind dependency order, and the registration handles authors hand to app
code. One declaration point means there is no second list to keep in
agreement, and no drift between what may be registered and what is loaded.

## Requirements

### Requirement: Single declaration point

A framework MUST be declared as exactly one object carrying the closed kind set and
the inter-kind dependency order. No other public surface SHALL accept a kind-set
declaration, so a second, conflicting declaration point cannot exist.

#### Scenario: Kinds are stated once

- **WHEN** a framework is declared with kinds `models` and `views`
- **THEN** that single declaration is the source of the registry's closed kind set and
  of module discovery, with no second kind list to keep in agreement

#### Scenario: Dependencies ride the same declaration

- **WHEN** the declaration states that `views` depends on `models`
- **THEN** modules of kind `models` are loaded and initialized before modules of kind
  `views` in every app, with no separate ordering declaration

### Requirement: Per-kind registration handles

The framework object MUST hand out a registration handle for any declared kind.
Requesting a handle for an undeclared kind MUST fail immediately, naming the unknown
kind and the declared set.

#### Scenario: Handle for a declared kind

- **WHEN** the author requests a registration handle for `models`
- **THEN** a handle is returned that registers objects under kind `models` in the
  framework's registry

#### Scenario: Handle for an undeclared kind

- **WHEN** the author requests a handle for `controllers` and the declared set is
  `models, views`
- **THEN** the request fails naming `controllers` and listing `models, views`

### Requirement: Handles need no wrapper code

A registration handle MUST be directly usable to mark objects, in both a bare form
(deriving the object name from the object itself) and a named form (an explicit
conforming name), without the framework author writing any wrapping logic. Names
follow the object-identity capability: derived names are converted, stated names are
verbatim, and both are validated.

#### Scenario: Bare form

- **WHEN** an object is marked with the bare handle
- **THEN** it is registered under the name derived from its own name

#### Scenario: Named form

- **WHEN** an object is marked with the handle and an explicit conforming name
- **THEN** it is registered under the explicit name

### Requirement: Declaration precedes boot

Registration handles MUST be obtainable from a framework that has not started, so app
modules can mark objects at load time. Marks are collected into the registry during
the framework's discovery phase.

#### Scenario: Handles before start

- **WHEN** a framework is declared and handles are taken before any start step
- **THEN** the handles are valid, and objects marked by them appear in the registry
  once discovery has run
