## Why

The registry already has a machine-readable projection. Nobody chose it, and it is a type
stub.

`spoc stubs` runs a collect-only boot and turns the result into `.pyi` text. That stub is
today the only external, machine-readable description of what a project registered, so any
tool wanting to know what is in a registry — a router generator, an admin surface, a
documentation build, another language's client — will parse a type stub. A `.pyi` then
becomes an interface it was never designed to be, and its emission rules become a
compatibility obligation for reasons unrelated to type checking.

Inside the codebase the same absence shows up as duplication. Two private structures
already describe one registry:

| | `diagnostics.RecordInfo` | `stubs.manifest.Entry` |
| --- | --- | --- |
| identifier, kind, namespace, object_name | yes | yes |
| where the object lives | `location` | — |
| shape and static type | — | `shape`, `type_ref` |
| boot depth | full boot | discovery only |
| serializable | no | no |

Four fields in common, two subpackages, neither able to leave the process. Rule 7 says
consolidate duplicates rather than add a third.

The long-horizon argument is the one that decides it. `kind:namespace.object_name` is the
most durable thing this project owns: a naming standard, not a Python API, implementable
and queryable by systems that never import `spoc`. A documented data projection is what
makes that portable, and Rule 9 says adopt the global standard — JSON Schema — rather than
invent a description format. Like the ordering contract, this is a one-way door: after the
first stable major release, the shape people scrape is the shape that must be supported.

## What Changes

- A **documented projection of a booted registry as data**: for every component, its
  canonical identifier, kind, namespace, object name, the location of the registered
  object, and its shape (constructible, callable, or value); plus the project's declared
  kind set.
- A **published JSON Schema** for that document, so any consumer in any language can
  validate it without reading Python.
- A **CLI subcommand** emitting it on standard output, and a **library function** returning
  the same structure, so the projection is not CLI-only.
- The projection is produced by a **collect-only boot** — discovery without initialization —
  so describing a project does not require its startup hooks to succeed.
- `stubs.manifest` becomes a **consumer** of the shared projection rather than the owner of
  a private one; the stub's own type-reference extraction stays where it is, because it is
  a Python-specific concern the projection does not carry.
- Emitted in **canonical-identifier order**, matching the rule the stub already follows, so
  a diff of two projections reflects the registry and nothing else.

## Capabilities

### New Capabilities

- `registry-projection`: the registry described as data — content, ordering, stability, and
  the schema that validates it.

### Modified Capabilities

- `typed-registry-stubs`: the stub manifest is stated as a consumer of the projection, so
  the two descriptions of one registry cannot drift apart.

## Impact

- New module owning the projection and its serialization, placed so that both
  `spoc.stubs` and any future consumer depend on it rather than on each other.
- `src/spoc/stubs/manifest.py` — `Entry` and the parts of `Manifest` that duplicate the
  projection are replaced by it; `type_ref` extraction stays.
- `src/spoc/cli.py` — one more subcommand registered on the composed parser, staying a thin
  adapter.
- A published JSON Schema file, and the `public` stability tier gains the projection's
  document shape — the deliberate cost of this change, taken knowingly before 1.0.
- `docs/architecture/kernel.md` — the projection is a surface derived from the registry and
  belongs in the diagram.
- No new dependencies: the standard library reads and writes JSON, and `spoc.formats`
  stays uninvolved because the kernel's own surfaces do not route through it.
