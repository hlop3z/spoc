# Design — Framework Object API

## Context

The registry-first kernel (archived change `registry-first-kernel`) fixed identity and
storage but left the authoring surface as three artifacts that must agree by hand:
`Components(*kinds)`, hand-rolled decorators, and `Schema(modules=[...])`. Real usage
(the bundled example, and zmag downstream) shows the resulting drift, a circular-import
workaround (`_components.py` modules existing only so decorators can predate the
framework), import-side-effect finalization, and config split across `spoc.toml` and
`settings.py`. The user's decisions, recorded up front: explicit `start()` (no lazy or
auto-boot), and `spoc.toml` as the only kernel-read config, with `settings.py` left to
users for constants and conditional logic the kernel never sees.

## Goals / Non-Goals

**Goals:**

- One public object (`Framework`) declares kinds, dependencies, and hooks once.
- Framework-author boilerplate for the example drops from ~60 lines to under 10.
- Pure construction; all side effects in `start(base_dir)`; `on_ready` finalize phase.
- Kernel reads `config/spoc.toml` (or `spoc.toml`) only; `settings.py` is never
  imported by spoc.
- Docs teach exactly one path.

**Non-Goals:**

- Typed per-kind component metadata (zmag's `config={}` smuggling) — future change.
- Per-kind strict/loose optionality — future change; `mode` survives as-is for now.
- A CLI / project scaffolder — attractive later, out of scope here.
- Any change to identifier grammar, registry semantics, or resolution.

## Decisions

### D1 — `Framework` absorbs `Components` and `Schema`

`Framework(*kinds, dependencies=None, mode="strict")` is the whole declaration.
Internally it still composes `Importer` → `Registry` (unchanged); `Components` becomes
an internal detail of `framework.kind()`, and `Schema` / `Hook` are deleted from the
public surface. Alternative considered: keep `Schema` as an optional advanced input —
rejected; a second declaration path is exactly the disease.

### D2 — `framework.kind(name)` returns a ready decorator

The returned callable supports `@model` and `@model(name="...")` (the
`functools.partial` dance moves inside the kernel, written once). Requesting an
undeclared kind raises `UnknownKindError` immediately. Alternative: attribute magic
(`framework.models`) — rejected as too implicit and collision-prone with real
attributes.

### D3 — Two-phase lifecycle: `__init__` declares, `start(base_dir)` boots

`start` does, in order: inject apps dir → load `spoc.toml` → collect app list (mode
cascade) → register modules → load plugins → discover components → fire `on_ready`
callbacks → init modules. Second `start` raises `SpocError`. `shutdown()` on a
never-started framework is a no-op. `base_dir` is an explicit required argument (user
decision: no upward auto-discovery).

### D4 — `on_ready` is a decorator-registered callback list

`@framework.on_ready` appends `Callable[[Registry], Any]`; fired in registration order
inside `start`, after discovery, before module initialization hooks. Errors propagate
and fail start. This replaces the import-side-effect finalize pattern (zmag's
`build_models`). Lifecycle hooks per module survive but move to
`framework.on_startup(kind)` / `framework.on_shutdown(kind)` decorator registrars,
replacing the `Schema.hooks` dict of `Hook` TypedDicts.

### D5 — Config: `spoc.toml` only; `settings.py` never read (ADR)

**Decision: Build (trivial) on stdlib `tomllib`, already adopted.** The kernel's
config surface is the existing TOML loader minus the settings-module machinery:
`load_configuration` (Python-module discovery/exec) is deleted; `INSTALLED_APPS` and
`PLUGINS` merge from settings is deleted; `[spoc.apps]` and `[spoc.plugins]` in
`spoc.toml` are the only inputs. The `.env/<mode>.toml` cascade stays (per
`project-configuration` spec). `Config.settings` field is removed; users import their
own settings module themselves if they want one — spoc never touches it. This also
makes the library importable standalone (no `config` package needed on `sys.path`),
fixing the testability complaint observed in zmag.

### D6 — Core vs adapters, dependency direction

Pure core (unchanged): `identifier`, `registry`, `components_discovery`, `utils`.
Boundary adapters: `toml_core`/`config_loader` (filesystem+TOML), `inject_apps`
(`sys.path`), `importer` (Python import system). `Framework` is the composition root
and the only place they are wired; it contains no parsing, no path math, no import
logic of its own. Dependencies keep pointing inward: adapters import core, never the
reverse. `examples/http_app.py` remains the thin-surface proof.

### D8 — Derived names normalize; explicit names and lookups do not

`@model class UserAccount` registers as `user_account`. The conversion happens in
exactly one place — the declaration layer (`components.component`), on the value
derived from `__name__` — and the result is then validated by the same
`validate_segment` as everything else, so `class 2Cool` still fails loudly.

Three boundaries stay strict, which is what keeps this from becoming "the system
guesses":

1. **Explicit `name=` is verbatim.** If the author states an identifier, it is used or
   rejected, never rewritten. Stating a name is an act of naming.
2. **`identifier.py` is untouched.** `validate_segment`, `parse`, and `compose` remain
   pure and strict; the grammar module is still the single authority, and normalization
   is a *derivation* step layered above it, not a weakening of it.
3. **Resolution never converts.** `resolve("models:blog.UserAccount")` fails. One
   canonical identifier per object survives intact.

This **reverses** the archived `registry-first-kernel` note that "`case_style` is never
called on the registration path" — it now is, deliberately, and `case_style` is
therefore load-bearing rather than vestigial. Rationale for the reversal: requiring
`name="user_account"` on every PEP 8 class taxed the author for a mechanical
transformation the kernel can do correctly, contradicting the convention-over-
configuration goal that motivates this whole change. Rejecting is still right for
values a human *stated*; it was wrong for values the kernel *derived*.

Alternative considered: normalize explicit names too — rejected, it makes `name=`
unpredictable and erases the escape hatch. Alternative considered: keep strict
derivation and lint for it — rejected, that is the boilerplate we set out to delete.

### D7 — Breaking release, no compatibility shims

Pre-1.0, downstream (zmag) pins an older version. `Components`, `Schema`, `Hook`,
`load_configuration` are removed outright; version bumps minor (0.x convention:
breaking allowed). Alternative: deprecation aliases for one release — rejected; two
ways to do everything is the problem being solved, and tests already pin absence of
removed API as the pattern (`test_framework.py`). Confirmed by the user at the
`/ai:decide` gate: green-field, no backward compatibility.

### Decision: TOML config parsing — Adopt stdlib `tomllib`

- **Status**: approved
- **Why**: standard-format parsing is never hand-rolled; `tomllib` is the standard
  library implementation and keeps the kernel zero-dependency.
- **Considered**: `tomli` (redundant on ≥3.11), `tomlkit` (round-trip editing we
  don't need).
- **Isolation**: `core/toml_core.py` adapter — the only module that imports it.

### Decision: Dependency ordering — Adopt stdlib `graphlib.TopologicalSorter`

- **Status**: approved
- **Why**: the hand-rolled `DependencyGraph` (~130 lines incl. cycle detection)
  duplicates stdlib `graphlib`; zero differentiating value, strictly more code to
  maintain.
- **Considered**: keep hand-rolled implementation (rejected — stdlib duplicate);
  `networkx` (rejected — heavyweight dependency for one algorithm).
- **Isolation**: internal to `core/importer.py`; `graphlib.CycleError` is translated
  to `CircularDependencyError` so the public error contract is unchanged.

### Decision: Lifecycle hooks — Build (hand-written, in-kernel)

- **Status**: approved
- **Why**: the contract is an ordered callback list fired once (`on_ready`) plus
  per-kind startup/shutdown — trivial scope; adopting a plugin framework would trade
  the kernel's zero-dependency guarantee for ~5% feature use.
- **Considered**: `pluggy` (mature, pytest-proven, but built for open plugin
  ecosystems with hookspec/hookimpl discovery); `stevedore` (entry-point loading,
  wrong problem).
- **Isolation**: `Framework` composition root; callbacks receive only the public
  `Registry` read surface.

### Decision: Registry + decorator factories — Build (existing kernel core)

- **Status**: approved
- **Why**: the `kind:namespace.object_name` grammar, closed kind set, per-segment
  resolution errors, and validate-never-normalize are the product's differentiating
  value; no OSS registry implements this contract (best match covers ~40%).
- **Considered**: `catalogue` (explosion — lightweight namespaced registries, no
  identity grammar); `class-registry` (factory pattern + entry points, wrong model).
- **Isolation**: pure core (`core/identifier.py`, `core/registry.py`);
  `framework.kind()` is a thin factory over the existing registration path.

## Risks / Trade-offs

- [Registration handles taken from one framework, apps loaded by another] → handles
  bind to their framework instance; discovery only collects marks made through the
  starting framework's own handles. Documented; two-instance independence test extends
  to handles.
- [`settings.py` removal breaks users relying on `INSTALLED_APPS` merge] → BREAKING is
  explicit in proposal; migration line in docs: move lists into `[spoc.apps]`.
- [`on_ready` ordering surprises when multiple callbacks depend on each other] →
  documented guarantee: registration order, single fire; anything fancier belongs in
  the callback itself.
- [Example/docs drift] → example is rewritten in the same change set (Rule 8); docs
  pages are tasks, not follow-ups.

## Migration Plan

Single change set on a branch: kernel rewrite → tests → example → docs → sync specs →
archive. No data migration; consumers upgrade by rewriting their composition file
(one page of docs shows old → new side by side once, in the release notes, not in the
docs body).

## Open Questions

- None blocking. Typed metadata and per-kind optionality are noted as future changes
  in Non-Goals.
