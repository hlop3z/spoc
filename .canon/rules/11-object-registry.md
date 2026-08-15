# Rule 11 — Universal object identifiers and the kernel registry

**Trigger:** naming or registering any system object — scalar, model, event — or designing
how the runtime discovers and resolves them.

Every system object has exactly one identifier, in one grammar, held in one registry. This is
the system's shared language: domains, APIs, events, storage adapters, and external
integrations all speak it.

## The grammar

```
<kind>:<namespace>.<object_name>[.<operation>]
```

- Every segment is **lowercase `snake_case`**: `^[a-z][a-z0-9_]*$`. No exceptions, no other
  casing anywhere in the system's naming.
- **`kind`** — the object category; determines how the runtime manages and interprets it.
- **`namespace`** — ownership. For domain objects this **is** the bounded context from
  Rule 10; `core` is reserved for the kernel's own objects.
- **`object_name`** — the specific object.
- **`operation`** — appended only at resolution time (`model:blog.post.create`), never part
  of the registered identifier.

An identifier is a **contract**: renaming a registered object is a breaking change, treated
with the same weight as breaking an API.

## Kinds

The kind set is **closed and deliberate** — a new kind changes what the runtime must know how
to manage, so introducing one is a recorded decision (`DECISIONS.md`), not an ad-hoc addition.

| Kind     | Holds                | Examples                                        |
| -------- | -------------------- | ----------------------------------------------- |
| `scalar` | primitive types      | `scalar:core.int64`, `scalar:core.uuid`         |
| `model`  | domain entities      | `model:blog.post`, `model:identity.user`        |
| `event`  | immutable domain facts | `event:commerce.order_created`                |

### `scalar` — the shared type system

Go-style names in the `core` namespace: `string`, `bool`, `int32`, `int64`, `float32`,
`float64`, `decimal`, `uuid`, `datetime`. Each scalar **must map 1:1** onto a JSON Schema /
OpenAPI type-and-format pair (Rule 9) — a scalar that can't be expressed in the standards is
not a scalar, it's a model. One definition drives every projection: OpenAPI, JSON Schema,
language mappings, database columns, serialization.

### `model` — domain entities

Namespace = bounded context. A model is the full definition of an entity: fields (typed by
registered scalars), relationships (by registered identifier), validation rules, commands,
queries, emitted events, permissions, and lifecycle. Cross-context references use the
identifier, never a foreign context's internals (Rule 10).

### `event` — immutable facts

Named **`noun_verb`, past tense**: `order_created`, `post_published`, `user_registered` — an
event is a fact about a thing, and this sorts every entity's events together in the registry.
Each event registers its schema (AsyncAPI-described, Rule 9), an explicit **version**,
metadata, source namespace, and consumers. Events are append-only: changing a published
event's schema means a new version, never an edit.

## The registry

The kernel (Rule 10) maintains **one** registry of every object. It is the single source of
truth for schema discovery, API generation, validation, serialization, permissions, runtime
resolution, and documentation generation — all of these are **projections of the registry**,
never independently maintained. If generated docs or an OpenAPI file disagree with the
registry, the registry wins and the projection is regenerated (Rule 8's docs-match-code, with
the registry as the code).

Nothing bypasses it: an object the registry doesn't know is an object the system doesn't have.

## Runtime resolution

```
do("model:blog.post.create", context, headers)
do("event:commerce.order_created.publish", context, headers)
```

Resolution order is fixed: **kind → namespace → object → operation**. Each step fails with a
precise error naming the segment that didn't resolve — a typo in an identifier must never
fall through to undefined behavior.

## Guardrails

- One grammar. Any object named outside `kind:namespace.object_name` is a defect.
- Casing is validated at registration, not by convention — reject, don't normalize.
- No unregistered objects; no second registry; no side-channel lookups.
- Registered identifiers are append-only in practice: rename = deprecate + add + migrate.
- The registry is runtime data with one schema of its own — externalized per the guidelines,
  not scattered through code as string literals.
