# Framework Declaration — Delta

## ADDED Requirements

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
