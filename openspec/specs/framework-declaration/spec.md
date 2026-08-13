# Framework Declaration

## Purpose

A framework is declared exactly once, on one object: its closed kind set, the
inter-kind dependency order, and the registration handles authors hand to app
code. One declaration point means there is no second list to keep in
agreement, and no drift between what may be registered and what is loaded.

## Requirements

### Requirement: Single declaration point

A framework MUST be declared as exactly one object carrying the closed kind set and,
for each kind, everything the kernel knows about it: its position in the inter-kind
dependency order, whether its modules are required or optional, and the metadata
contract its components carry. No other public surface SHALL accept a kind-set
declaration or any per-kind attribute, so a second, conflicting declaration point
cannot exist and no kind attribute can be stated away from the kind it describes.

Declaring the same kind more than once within one declaration MUST fail, naming the
duplicated kind. A later declaration never silently replaces an earlier one.

The inter-kind dependency order stated here MUST hold across the whole project, not
merely within each app. A kind that depends on another orders every installed app's
modules of the two kinds against each other, so the depended-on kind is complete
everywhere before the dependent kind begins anywhere. The declaration is therefore the
single statement of load phases for the project, and no per-app declaration weakens or
overrides it.

#### Scenario: Kinds are stated once

- **WHEN** a framework is declared with kinds `models` and `views`
- **THEN** that single declaration is the source of the registry's closed kind set and
  of module discovery, with no second kind list to keep in agreement

#### Scenario: Dependencies ride the same declaration

- **WHEN** the declaration states that `views` depends on `models`
- **THEN** modules of kind `models` are loaded and initialized before modules of kind
  `views`, with no separate ordering declaration

#### Scenario: The dependency order spans apps

- **WHEN** the declaration states that `views` depends on `models`, and two apps `blog`
  and `shop` are installed
- **THEN** both apps' `models` modules are loaded and initialized before either app's
  `views` module
- **AND** no app's `views` module is loaded before any app's `models` module, whatever
  order the apps are declared in

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

### Requirement: Lifecycle hooks may be synchronous or asynchronous

A kind's startup and shutdown hooks MUST be declarable as either plain
functions or coroutine functions, on the same declaration attribute. The
declaration accepts both without ceremony; which lifecycle path may dispatch a
coroutine hook is the lifecycle capability's contract. Nothing about declaring
an asynchronous hook changes the kind's other attributes.

#### Scenario: Coroutine hook declared

- **WHEN** a kind is declared with a coroutine function as its startup hook
- **THEN** the declaration is accepted, and the hook is dispatched by the
  asynchronous lifecycle path exactly as a plain hook is dispatched by either
  path

#### Scenario: Mixed hooks across kinds

- **WHEN** one kind declares a plain startup hook and another declares a
  coroutine startup hook
- **THEN** both declarations are accepted on the same attribute, and each hook
  runs on a lifecycle path that supports it

### Requirement: Declaration precedes boot

Registration handles MUST be obtainable from a framework that has not started, so app
modules can mark objects at load time. Marks are collected into the registry during
the framework's discovery phase.

#### Scenario: Handles before start

- **WHEN** a framework is declared and handles are taken before any start step
- **THEN** the handles are valid, and objects marked by them appear in the registry
  once discovery has run
