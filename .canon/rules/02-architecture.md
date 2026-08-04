# Rule 2 — Pure core, adapters at the boundaries

**Trigger:** writing or restructuring any code that touches a framework, network, database,
filesystem, queue, or external API — and any change to what lives in the core.

**The dependency rule:** dependencies point inward. Infrastructure may depend on the core; the
core must never depend on infrastructure.

## The core must be

- **Framework-free** — no HTTP, GraphQL, ORM, queue, filesystem, cloud SDK, or config-loading
  imports.
- **Deterministic where practical** — clock, randomness, and IDs injected through interfaces.
- **Testable with zero infrastructure running.**
- **Composable** — behavior lives once, as small units that snap together.

## Boundaries use ports and adapters

| External concern           | Adapter type                                    | Lives in                |
| -------------------------- | ----------------------------------------------- | ----------------------- |
| HTTP / GraphQL handlers    | application adapter                             | `adapters/controllers`  |
| Database access            | infrastructure adapter implementing a repo port | `adapters/repositories` |
| External APIs              | integration adapter                             | `adapters/gateways`     |
| Message queues             | messaging adapter                               | `adapters/messaging`    |
| Filesystem / cloud storage | storage adapter                                 | `adapters/storage`      |

Paths are the default shape; use the project's equivalent layout where one already exists.

## Do

- When the core needs an external capability, define a **port** (interface) in the core and
  inject the adapter implementation at composition time.
- Keep entry points thin: every surface (CLI, GUI, API) translates transport ↔ use-case request
  and response only. No business logic, branching, or state of its own.
- Map at the adapter — ORM and driver objects never reach the core as entities.

## Don't

- Don't impose the full pattern on trivial glue or simple CRUD scripts where it is pure
  ceremony. **But** framework types never leak into existing core modules, however small the
  change.

Artifact-layer separation (WHAT / HOW / DO) is a different axis — see `.canon/guidelines.md`.
