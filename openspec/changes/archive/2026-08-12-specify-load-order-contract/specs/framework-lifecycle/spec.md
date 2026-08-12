## ADDED Requirements

### Requirement: Load order is a stated total order

The framework MUST load and initialize app modules in a total order determined by exactly
two things, in this precedence: the depth of a module's kind in the declared inter-kind
dependency order, and the position of the module's app in the effective installed-app list.
Kind depth decides first; the app list breaks every remaining tie. Two starts of the same
project MUST produce the same order, and the order MUST NOT depend on filesystem layout,
dictionary iteration, or the order in which modules happen to import one another.

A kind's depth MUST be read from the declaration, never from which modules were found. An
app that omits an optional kind therefore changes the position of no module but its own:
the omission MUST NOT move that app's remaining modules into an earlier phase, and MUST NOT
reorder any other app.

Because kind depth is the first key, the modules of one kind form a load phase that
completes across every installed app before the next phase begins. Because the installed-app
list is the tiebreak, an author who needs one app's modules of a kind to load before
another's states that by ordering the app list, and no other declaration is required.

The order MUST be a property the framework states rather than one inherited from a
third-party ordering utility, so that a change of implementation cannot silently weaken it.

#### Scenario: Kind depth decides before app position

- **WHEN** apps `blog` and `shop` are installed in that order, and kind `views` depends on
  kind `models`
- **THEN** the load order is `blog.models`, `shop.models`, `blog.views`, `shop.views`

#### Scenario: App list order breaks the tie within a phase

- **WHEN** the same two apps are installed in the order `shop`, `blog`
- **THEN** `shop.models` is loaded and initialized before `blog.models`
- **AND** both are still loaded and initialized before either app's `views` module

#### Scenario: The order is stable across starts

- **WHEN** the same project is started twice in one process, with a shutdown between
- **THEN** both starts load and initialize modules in the same order

#### Scenario: An omitted optional kind moves nothing else

- **WHEN** kinds `models`, `views`, and `urls` each depend on the previous one, `views` is
  optional, apps `blog` and `shop` are installed in that order, and `shop` has no `views`
  module
- **THEN** the order is `blog.models`, `shop.models`, `blog.views`, `blog.urls`, `shop.urls`
- **AND** `shop.urls` is loaded and initialized after every app's `views` module, exactly as
  it would be if `shop` had one

#### Scenario: A cycle in the declared kind order is refused

- **WHEN** the declared kinds contain a dependency cycle
- **THEN** start fails naming the cycle, and no ordering is produced

### Requirement: Lifecycle hooks fire in load order

The framework MUST fire each kind's startup hook, and each module's own initialization, in
the load order stated above, and MUST fire the paired shutdown work in the exact reverse.
Hook firing is the surface through which load order is observable, so the two MUST NOT be
allowed to diverge: a startup hook for a dependent kind MUST NOT run before the startup
hook of a depended-on kind has run for every installed app.

#### Scenario: A dependent kind's hook sees every app's contribution

- **WHEN** kind `views` depends on kind `models`, two apps are installed, and both kinds
  declare startup hooks
- **THEN** the `models` startup hook has run for both apps before the `views` startup hook
  runs for either

#### Scenario: Teardown reverses the load order exactly

- **WHEN** a started framework with two apps and two dependent kinds is shut down
- **THEN** shutdown work runs in the exact reverse of the order in which startup work ran

### Requirement: No declaration may invert the phase order

The framework MUST NOT provide any way to declare that a module of a deeper kind loads
before a module of a shallower kind, in the same app or across apps. Ordering between apps
is expressible only within one kind phase. A declaration form whose meaning would place a
whole app ahead of another app's earlier-phase modules MUST be refused, because the phase
guarantee cannot survive it.

#### Scenario: Ordering between apps stays inside a phase

- **WHEN** any supported declaration orders one app against another
- **THEN** that ordering affects only the relative position of their modules within each
  kind phase
- **AND** it never moves a module of one kind ahead of any module of a kind it depends on
