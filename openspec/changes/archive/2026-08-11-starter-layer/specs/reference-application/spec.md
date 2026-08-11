# Reference Application — Delta

## ADDED Requirements

### Requirement: The resource lifecycle convention is demonstrated

The reference project MUST demonstrate the resource lifecycle convention: it declares
at least one process-lifetime resource under the conventional resource kind, opened by
that kind's startup hook, resolved through the registry by at least one component in
another module while handling a call, and released by the kind's shutdown hook. The
demonstration MUST use only public kernel contracts, and the test suite MUST exercise
it, so the recipe the documentation teaches can never silently drift from what the
kernel does.

#### Scenario: The resource is opened at start and reached through the registry

- **WHEN** the reference project starts and a component that depends on the resource
  handles a call
- **THEN** the component obtains the live resource by resolving its canonical
  identifier through the registry

#### Scenario: The resource is released at shutdown

- **WHEN** the reference project shuts down
- **THEN** the resource's release action has run, and the test suite observes both the
  open and the release
