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
