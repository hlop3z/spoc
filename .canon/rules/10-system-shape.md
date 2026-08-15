# Rule 10 — Modular monolith on a kernel; DDD, events, and separated reads/writes

**Trigger:** starting a system or service, adding a bounded context, or deciding deployment
shape.

## Deployment shape: modular monolith by default

**One deployable, many packages.** Microservices only when the user explicitly specifies
them — network boundaries are the most expensive boundaries there are, and they are earned by
scale evidence, not assumed.

Use the language's workspace mechanism (Cargo workspaces, uv workspaces, or the equivalent)
to keep the monolith modular:

- **One package per bounded context**, plus the kernel and the adapters.
- Each context package depends only on the kernel and its own domain — never on another
  context's internals. Cross-context communication goes through events or defined ports.
- A context that respects this is **extraction-ready**: it can become a standalone service
  later by swapping the in-process transport for a network one, without rewriting the domain.
  Prepare for that; don't pay for it early.

## Kernel/runtime

The core engine provides the execution model — composition root, lifecycle, event
dispatch, configuration, and the **object registry** (Rule 11) through which every scalar,
model, and event is named, discovered, and resolved. Applications and services are modules
registered on it. The kernel knows no domain; contexts know no infrastructure (Rule 2's
dependency direction, applied at system scale).

## Domain model: DDD

- Explicit **bounded contexts** with their own models and language; translation at the
  boundary, never a shared god-model.
- Aggregates enforce invariants; domain logic stays pure and framework-free (Rule 2).

## Communication: events where decoupling matters

- **Within** a context: direct calls. Async adds latency and failure modes; it must buy
  decoupling to be worth it.
- **Between** contexts: prefer domain events over direct dependency. Event contracts are
  AsyncAPI-specified (Rule 9).

## Reads and writes: separated

- **Always**: query/mutation separation — commands change state and return little; queries
  return data and change nothing.
- **Where the domain warrants it**: full CQRS with independent read models, and event
  sourcing where history *is* the domain (audit trails, temporal queries, replay). These are
  heavy machinery — gate them per context with a recorded decision, not as a blanket default.

## Simplicity discipline

Match complexity to the context's actual weight. A trivial supporting context gets a module
and a repository, not aggregates, event streams, and read models — the full pattern applied
to trivial code is ceremony (Rule 2's own caveat, restated at system scale). Layers evolve
independently; coupling that prevents that is the defect to hunt.

Persistence stays behind ports (Rule 2) — PostgreSQL, MySQL, document stores, object storage,
or plain files are adapter choices recorded in the change's `design.md` or `DECISIONS.md`,
invisible to the domain.
