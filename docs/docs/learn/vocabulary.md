# The Default Vocabulary

!!! note "One word, two spellings"
    The beginner pages say **block**; the API says **`Component`**. They are the
    same thing: a block is what you decorate, and after `start()` it sits on the
    shelf as a `Component` record in `framework.registry` — identifier, facets,
    and the object itself. Everything a block "is" lives on that record; see
    [Name Tags & the Registry](names-and-registry.md) for the mapping and
    [the API reference](../api/public.md) for the record's fields.

SPOC lets you invent any kinds you like — that's the whole point. But an ecosystem
needs a shared language: a reusable app published by someone else can only declare
components of kinds *your* project happens to have. So SPOC blesses one **default
vocabulary** — five kinds with agreed meanings.

**The rule, up front:** deviate freely. Nothing enforces these names. The default is
what the starter template emits, what these docs teach, and what reusable third-party
apps may assume. Think of it like Django's `models.py`: powerful *because* everyone
means the same thing by it — except here it's a convention, not a law.

## The five kinds

| Kind        | A component is…                                    | Lifecycle role                                  |
| ----------- | -------------------------------------------------- | ----------------------------------------------- |
| `models`    | a domain data declaration (a class, a schema)      | none — purely declarative                       |
| `views`     | a callable a surface exposes (a route, a page)     | none — a surface projects it                    |
| `commands`  | a callable a project CLI exposes                   | none — the CLI projects it                      |
| `resources` | a live process-wide object (a pool, a client)      | opened by `on_startup`, closed by `on_shutdown` |
| `hooks`     | a callable a surface fires at named moments        | none — *your* code dispatches it                |

Four of the five are purely declarative: SPOC registers them, and a **surface** — the
web binding, the CLI, the worker loop you build — enumerates the registry and exposes
them. That's the projection pattern from
[Name Tags & the Registry](names-and-registry.md).

`resources` is the interesting one.

## Resources: live objects with a lifecycle

Every application has a few objects that must be **opened once, shared everywhere,
and closed on the way out** — a database pool, an HTTP client, a cache connection.
Most frameworks hand you an untyped bag for these (`app.ctx.db`, `app.state`). SPOC
already has something better: the registry.

The recipe is three small pieces, all public API you've already met: declare the
kind with `on_startup`/`on_shutdown` hooks (the only kind in the vocabulary that
uses them), register each resource as an *instance* that knows how to `open()` and
`close()` itself, and resolve it through the registry at call time. The complete,
runnable project is [Add a Database](../how-to/add-a-database.md) — this page keeps
the reasons.

On `start()`, the kind's `on_startup` opens every declared resource before your
surface takes traffic; on `shutdown()`, `on_shutdown` closes them in reverse module
order. And because shutdown replaces the registry, resolving a resource after
teardown fails with a **named error** — you can never be handed a dead pool.

Three fine points:

- **Resolve at call time, not import time.** A module that grabs a resource at import
  runs before `start()` and gets nothing. Inside a view/command/hook body, the
  resource is always live.
- **If a module's own `initialize()` needs a resource**, declare the order:
  `spoc.KindSpec("models", depends_on=("resources",))`. That works across apps too —
  a kind is a phase, so every app's `resources` is up before any app's `models`. What
  you cannot order that way is two apps' modules of the *same* kind; for those, the
  `[spoc.apps]` list decides, or resolve lazily.
- **Async projects** declare coroutine `open`/`close` hooks and boot with
  `astart()`/`ashutdown()` — same recipe, awaited. See
  [Start & Stop](lifecycle.md).

## Hooks: events without an event system

A `hooks` component is a callable; *dispatching* it is your surface's job, not
SPOC's — the kernel describes, it never executes. The pattern is one loop:

```python test="skip"
for record in framework.registry.by_kind("hooks"):
    record.object(event)          # your surface decides when, and with what
```

Name hook components after the moment they answer (`on_order_created`,
`before_request`) and every app can contribute to the same moments.

## Where to see it running

The [storefront example](../examples.md) exercises the resource recipe end to end —
a resource opened at boot, resolved from another module mid-call, and closed at
shutdown, with the test suite watching both halves. The starter template
(`spoc init myproject --template starter`) generates the full vocabulary wired and
running.

Next: [Plugins](plugins.md).
