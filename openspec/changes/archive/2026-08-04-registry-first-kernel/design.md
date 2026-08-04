# Design — registry-first-kernel

## Context

SPOC (~2,700 LOC, zero runtime dependencies, Python ≥3.13) is adopted as the studio's
runtime kernel: it manages internal resources and application objects underneath any
HTTP surface. The parts being kept — filesystem app discovery, dependency-ordered module
import, lifecycle hooks, TOML config with the development→staging→production mode
cascade, plugin loading — are sound. The registry is not:

- Two identifier grammars coexist. `Components.builder()` produces `app_object`
  (`components.py:342`) but is never called by the runtime; the actual store is
  populated by `Importer._get_module_objects` with keys like `auth.UserAccount`
  (`core/importer.py:375`).
- Registration silently drops objects when the component type string ≠ the module file
  name (`core/importer.py:374`), leaving an empty-but-present bucket.
- Instance identity is derived by walking the call stack (`_locate_obj`,
  `components.py:96`) and by mutating the caller's class to force hashability
  (`components.py:154-158`); `builder()` crashes on every registered instance.
- `get_component` returns `None` on any failure (`framework.py:171-175`).
- `Importer` is a process-global singleton with a class-level hook registry, so two
  frameworks cannot coexist and tests leak state.

Greenfield licence: SPOC is on PyPI with no users. Breaking changes are free; no
deprecation shims or compat views.

## Goals / Non-Goals

**Goals:**

- One canonical identifier grammar (`kind:namespace.object_name`) validated at
  registration — reject, never normalize (Rule 11).
- One flat registry of typed records; every grouped view is derived. External surfaces
  build projections by enumerating records through the public API alone.
- Per-segment, precise resolution errors.
- Kernel invariants made structural: **zero runtime dependencies** and
  **describes-never-executes** (the kernel never calls user code beyond lifecycle
  hooks).
- Instance-scoped composition: `Framework` owns its importer and hooks; no global state.

**Non-Goals:**

- Dependency injection / graph solving. Resolution is a lookup; wiring belongs to
  consumers (e.g. `svcs` adopted *on top of* the registry if ever needed).
- Invocation (`do(...)`), calling conventions, context/headers. No `.operation`
  identifier segment — it can be added later without breaking; removing one cannot.
- Event dispatch. The studio's event-sourced engine registers on the kernel as an app.
- Worker/execution primitives, HTTP anything, instance validation/serialization.
- Backward compatibility with the current API shape.

## Decisions

### D1 — Registry-first storage; grouped views are derived

One flat `dict[str, Component]` keyed by canonical identifier, owned by the importer
instance and exposed read-only through `Framework`. Facet queries (`by kind`,
`by namespace`) filter that store. The existing `SimpleNamespace`-of-dicts
(`framework.components.models`) is **not** kept — greenfield, one read API.

*Alternative considered*: keep dict-of-dicts and bolt on a flat index — rejected: two
stores to keep consistent, and the dict-of-dicts is exactly what made the `type ==
module` silent filter possible.

### D2 — `Component` record promoted onto the runtime path

`Component` (identifier, kind, namespace, name, object, config, metadata) is built at
registration time and is what the registry stores. `builder()` as a separate off-path
constructor disappears; `Internal.app_name`/`obj_name` (written, never read) are
deleted. This makes the record — already shaped like a projection row — the unit of
enumeration.

### D3 — Layout is taxonomy, validated loudly

`Schema.modules` is the closed kind set, fixed at composition time. Discovery keeps the
"objects in `models.py` are kind `models`" convention, but a declared component whose
kind does not match its module raises at startup naming object, kinds, and file
(replacing the silent `type_name == mod` filter). No runtime `add_type`;
`Components.add_type` collapses into schema declaration.

*Alternatives considered*: declaration-owns-taxonomy (kinds independent of layout) —
rejected as ceremony without a driving need; module-default-with-override — deferred,
backward-compatible to add later if a real two-kinds-per-file case appears.

### D4 — Identifier composed by the kernel, validated against `^[a-z][a-z0-9_]*$`

`namespace` = first segment of the declaring module's package (the app name);
`object_name` = the declared name. Every segment validated at registration; violation
raises naming segment and value. `case_style` survives as a pure projection utility
(e.g. rendering `post` as `Post` for a docs page) and is never applied during
registration. Consequence (intended): a class named `MyService` is a registration error
unless registered with an explicit conforming name.

### D5 — Explicit identity; delete stack inspection

Instances register as `register(kind, obj, name="...")`; a missing name on a nameless
object raises. `_locate_obj`, `_SKIP_NAMES`, and the `__class__`-mutation hashability
hack are deleted. Classes and functions may default their name from `__name__` **only
if it already conforms** (D4 — no normalization).

### D6 — `resolve()` replaces `get_component`; per-segment errors

`Framework.resolve(identifier: str) -> Component` parses the grammar, then checks kind →
namespace → object_name, raising a dedicated exception per step (extending the existing
`core/exceptions.py` hierarchy: e.g. `UnknownKindError`, `UnknownNamespaceError`,
`UnknownObjectError`, `MalformedIdentifierError`), each carrying the failing segment,
its value, and valid candidates. A four-segment identifier is malformed (Non-Goal:
operation). Errors are the contract — no `None` returns anywhere in the lookup path.

### D7 — De-globalize composition

Delete `core/singleton.py`. `Importer` becomes a plain class; `module_hooks` moves from
`ClassVar` + classmethod to instance state; `Framework` constructs and owns its importer.
Two frameworks in one process are independent; tests need no global resets.

### D8 — Scope-line deletions

`workers.py` (execution machinery — violates describes-never-executes), `tools.py` (a
second, parallel registry with its own `__is_tool__` metadata scheme), `types.py` and
`utils.py` (trivial shims) are deleted with their tests and docs. Anyone needing thread
wrappers has the stdlib.

### D9 — Build-vs-adopt ADRs (recorded by /ai:decide, 2026-08-04)

All three concerns share one hard constraint: the kernel's zero-runtime-dependency
invariant makes any in-kernel adopt a hard reject regardless of rubric score. Research
confirmed every candidate is healthy (svcs stable/Tidelift-backed; stevedore alive under
OpenStack; pluggy the pytest standard; dishka and dependency-injector both active) — the
rejections below are fit, not maturity.

#### Decision: object-identity — Build hand-written

- **Status**: approved
- **Why**: no library owns this grammar; a ~20-line stdlib-`re` validator versus a
  dependency plus a grammar file is not a contest.
- **Considered**: lark / parsimonious (general parser generators — overkill for a
  3-segment regex grammar, and each adds a runtime dependency).
- **Isolation**: one identifier module; the only place the grammar is defined or
  validated. Everything else calls `parse`/`compose`.

#### Decision: component-registry — Build hand-written

- **Status**: approved
- **Why**: the store is a dict plus facet filters; every mature candidate covers a
  *different* concern and none speaks `kind:namespace.object_name`.
- **Considered**: svcs (type-keyed service location with DI-shaped factories — executes
  user code, colliding with describes-never-executes; the noted consumer-side adopt if
  DI is ever wanted *on top of* the registry); pluggy (hook specs, no object identity
  model); stevedore (entry-point discovery — would replace SPOC's filesystem/TOML
  discovery, a keep-as-is item, not its registry).
- **Isolation**: registry lives in the importer instance, exposed read-only through the
  framework's public enumeration/facet API; surfaces touch records only.

#### Decision: component-resolution — Build hand-written

- **Status**: approved
- **Why**: resolution is a pure lookup with per-segment errors; extending the existing
  in-repo exception hierarchy is the whole job.
- **Considered**: dishka / dependency-injector (graph-wiring DI containers — adopting
  either is a scope change into the design's explicit Non-Goals, not a tool choice).
- **Isolation**: `Framework.resolve()` plus `core/exceptions.py`; no other module
  raises resolution errors.

### D10 — Docs shrink in the same change set (Rule 8)

Delete `advanced/workers.md`, `api/workers.md`, `api/tools.md`; rewrite `components`,
`framework`, `importer`, quick-start, and examples against the new grammar; reposition
`README.md` (kernel under any HTTP surface). Add `docs/architecture/` with a Mermaid
diagram of surfaces → kernel (registry ★) ← apps (Rule 1). Doc pages describing deleted
or changed behavior are defects if they survive this change.

## Risks / Trade-offs

- [Strict rejection breaks the familiar PascalCase-class ergonomics] → intended per
  Rule 11; escape hatch is an explicit conforming `name=` at registration, documented
  prominently in the migration notes and quick-start.
- [Layout-as-taxonomy can't express two kinds in one file] → accepted; D3's deferred
  override is a backward-compatible future addition if a real case appears.
- [Deleting `workers.py`/`tools.py` might orphan an undiscovered consumer] → greenfield
  licence says none exist; PyPI download counts are bot noise. Worst case: recover from
  git history as a separate package.
- [De-singletonizing changes import-side behavior some example code relies on] →
  examples are rewritten in this change; the FastAPI definition-of-done example is the
  regression net.
- [Registry key = full identifier string makes facet queries O(n)] → acceptable at
  studio scale (hundreds of components); facets can gain indexes later without API
  change.

## Migration Plan

Single change set, no phased deploy (no users). Order inside the change: grammar +
exceptions → registry + discovery rework → resolve() → de-singleton → deletions → docs
→ definition-of-done example. Rollback = git revert of the change set. Version bumps to
0.4.0 signaling the break.

## Open Questions

- None. The `/ai:decide` gate ran 2026-08-04; all three D9 decisions are approved.
