# Starter Layer — Design

## Context

The kernel (registry, kinds, lifecycle, diagnostics) is complete and its invariants are
validated by twenty years of precedent: Eclipse's declarative extension registry aged
well; OSGi's dynamic service registry did not; the failure mode was dynamism, which SPOC
already forbids ("nothing writes to the registry after boot", `framework.py:83-84`).
What the platform-ecosystem literature calls *boundary resources* — the vocabulary,
toolkits, and recipes third parties build against — is the empty layer this change fills.

Current state, concretely:

- `spoc init` defaults to kinds `models,views` and generates a project that prints its
  registry and exits. One built-in template set (`default`) exists.
- Live resources (a DB pool, an HTTP client) have every needed mechanism — kind
  `on_startup`/`on_shutdown`, the registry, `resolve`, registry replacement on shutdown
  (`framework.py:274-278`) — but no named convention. Flask/Sanic/FastAPI all fell back
  to untyped attribute bags here; SPOC's registry does this better but nothing says so.
- `load_spoc_toml` returns `{"spoc": merged}` (`src/spoc/core/config.py:135`), silently
  discarding every other top-level table in `spoc.toml`.

## Goals / Non-Goals

**Goals:**

- One documented conventional vocabulary that the default template emits, the docs
  teach, and the reference application exercises.
- A starter template set that generates a *runnable* application surface from the
  registry, as pure template data.
- App-owned `spoc.toml` tables reach the application through `Config`.
- Kind contribution recorded as deferred, with its known-good shape, so it never reads
  as an open question again.

**Non-Goals:**

- No kernel changes to registry, loader, identity, or declaration.
- No `spoc run` in SPOC's own CLI — the generated project owns its command entry point;
  the kernel never executes user code.
- No blessed transport: the starter generates no HTTP, messaging, or worker binding;
  bindings are documentation recipes over the generated projection module.
- No typed config binding, schema engine, or validation of app-owned tables — that is
  the application's job through the documented seam (ADR-3).
- No kind-contribution mechanism (ADR-4).
- No event-dispatch helper; a `hooks` kind plus user-called dispatch already fits the
  invariants, and the starter demonstrates it as convention only.

## Decisions

### ADR-1 — The vocabulary is convention, not mechanism

**Decision:** Bless five kinds as the documented default vocabulary:

| Kind | Meaning | Lifecycle use |
|---|---|---|
| `models` | domain data declarations | none (declarative) |
| `views` | callables a surface projects (routes, pages) | none (declarative) |
| `commands` | callables a project CLI projects | none (declarative) |
| `resources` | factories for live process-wide objects (pool, client) | kind `on_startup` opens, `on_shutdown` closes |
| `hooks` | callables a surface dispatches at named moments | none (dispatch is the surface's, user-called) |

`spoc init` keeps its current default of emitting `models,views` modules for a bare
project (the *starter* set emits the full vocabulary); the docs present the five as one
table with the rule "deviate freely — the default is what reusable apps may assume."

**Why:** every gap found in the framework comparison (Flask `g`/`app.extensions`, Sanic
`ctx`/signals, Django management commands, FastAPI lifespan) is an instance of a missing
*name*, not a missing mechanism. Ecosystem research says a platform needs homogeneity to
pool investment and variability to fit demand — a blessed-but-overridable vocabulary is
the textbook resolution. Alternatives considered: keep full neutrality (rejected: no
ecosystem can target it — Django's reusable apps exist because `models` means one
thing); enforce the vocabulary in the kernel (rejected: contradicts "SPOC lets you
write the rules" and needs kernel code where a convention suffices).

### ADR-2 — Resources live in the registry, not a context bag

**Decision:** the resource convention is: a `resources` module declares a component per
resource; the kind's `on_startup` hook constructs/opens the live object; apps reach it
with `framework.resolve("resources:<ns>.<name>")`; `on_shutdown` closes it. No new API.

**Why:** an `app.ctx`-style bag is a second registry with a worse grammar — this repo
already deleted `spoc.tools` for exactly that. Registry lifetime already equals resource
lifetime because `_reset()` replaces the registry on shutdown, so a stale handle is a
named resolution error, not a dead pool. OSGi's dynamism pain does not apply: the
registry is static between boot and shutdown. The one live risk is call-site friction
driving users to module globals (the only surviving part of the service-locator
critique); mitigated by making the recipe short and the starter demonstrate it, and
accepted otherwise.

### ADR-3 — Config passthrough: expose, don't validate; refuse nothing new

**Decision:** `load_spoc_toml` keeps every top-level table it parses. `Config` gains one
field (name settled at implementation, e.g. `tables`) carrying all top-level tables
other than `[spoc]`, deep-copied per load like the defaults. The `[spoc]` table's
closed-key contract is unchanged. The docs configuration page states the contract: SPOC
reads `[spoc]`; every other table is yours, delivered as parsed data; validate it with
the documented seam. The seam's tool choice (the obvious candidate is
pydantic-settings) is a build-vs-adopt call recorded via `/ai:decide` before
implementation — the kernel itself adopts nothing, so the decision only names what the
docs recommend.

**Why exposure over refusal:** refusing unknown top-level tables would make `spoc.toml`
unusable for the app's own settings and push projects back to a second config file —
the opposite of one declarative source. Flask/Django/Sanic validate nothing and won
anyway; FastAPI shipped nothing and the ecosystem standardized on an external validator.
The closed set stays where typos are SPOC's fault (`[spoc]` keys); app-table typos are
app bugs, catchable by the app's own schema through the seam. **Why not build
validation:** ecosystem already converged externally; canon forbids rebuilding it.

The seam's docs contract is tool-agnostic — "validate the parsed table with a schema
validator" — and its worked example uses plain pydantic (`Model.model_validate` over
the table `framework.config` exposes). Not pydantic-settings: its file/env source
machinery duplicates reading the kernel has already done. Decision block below.

### ADR-4 — Kind contribution: deferred, shape recorded (this note is the deliverable)

**Decision:** installed packages declaring their own kinds is *not built*. The
known-good shape, if ever needed: Eclipse extension points prove contributed
vocabularies stay compatible with a declarative, statically-knowable registry — but
only because every extension point carries its contributor's namespace
(`org.eclipse.ui.views`). SPOC's grammar has no owner slot in the kind segment, so
contribution requires a grammar decision (Rule 11) first: a contributed kind must be
namespaced by its contributing package, with `Framework(...)` remaining the app
author's root vocabulary. Until a concrete reusable-app ecosystem demands it, the
closed kind set stands. Do not reopen this from the archive; reopening requires an
actual third-party package that needs it.

### ADR-5 — The starter is surface-neutral template data; bindings are recipes

**Decision:** one new built-in template set (working name `starter`) beside `default`,
same manifest format, same `string.Template` substitution, no new scaffolder code
paths. It generates: the five-kind vocabulary wired through `framework.py`; a
**transport-neutral projection module** that derives abstract surface tables (routes,
commands, hooks) from registry records alone, importing nothing third-party — the
shape `examples/http_app.py:build_routes` already demonstrates; a **runnable
project-owned command surface** over the `commands` kind built on the standard
library's argument parser (Django's `manage.py` shape); a `resources` demo
(opened/closed via kind hooks); a `hooks` dispatch site in the command surface; and
the generated project's own manifest, which needs **no third-party runtime
dependency**. Transport bindings — HTTP, message sockets, workers — ship as short
runnable documentation recipes over the projection module, not as generated code; the
worked HTTP recipe uses the existing examples dev-dependency and runs under the
docs-tests policy.

**Why neutral (user decision, 2026-08-10):** the kernel's pitch is surface-plural —
"HTTP, CLI, workers … FastAPI, Robyn, anything." A starter that hardwires one
transport demotes every other to second-class and makes SPOC read as an adjunct of
that stack. Neutrality also erases, rather than mitigates, the "SPOC looks like stack
X" risk, and leaves the generated project as dependency-free as the kernel.
Alternatives considered: an HTTP-framework starter (rejected: the flavoring above;
accepted trade-off is that a web app is one ~15-line recipe away instead of out of
the box); per-stack starter sets now (rejected: each must generate-and-boot in CI for
no present user — remains open as later pure-data additions through the same
`scaffold-templates` contract).

### Decision: starter surface stack — Adopt stdlib (no third-party binding)

- **Status**: approved
- **Why**: the kernel is surface-plural; the starter teaches the registry projection,
  the stdlib command surface makes it runnable with zero dependencies, and transport
  bindings are runnable docs recipes (worked example: the existing examples
  dev-dependency).
- **Considered**: FastAPI-generating starter (flavors SPOC as an HTTP/FastAPI
  adjunct); Litestar (same flavoring plus a new CI dependency); per-stack sets now
  (CI cost per set, no present user).
- **Isolation**: template data only; the projection module is dependency-free; binding
  recipes live in docs and execute under the docs-tests dev group.

### Decision: settings-validation seam — Adopt pydantic (worked example only)

- **Status**: approved
- **Why**: the seam receives an already-parsed table, so plain-model validation is the
  exact fit; the docs contract stays tool-agnostic and pydantic appears only as the
  worked example.
- **Considered**: pydantic-settings (source-loading machinery duplicates reading the
  kernel already did); dynaconf (its own layering competes with the mode cascade); no
  named tool (the docs example would be pseudocode).
- **Isolation**: documentation only — the kernel neither imports nor depends on it;
  the example validates the table `framework.config` exposes.

### Core vs adapters, dependency direction, wiring

Unchanged and inherited: `config.py` remains the kernel's single file-reading adapter;
the `Config` record stays a frozen value object; templates are data loaded through the
existing scaffold ports; the generated project's surface modules are *its* adapters,
not SPOC's. Composition stays in `spoc/cli.py` (scaffold) and the generated project's
own entry points (runtime). Nothing new points outward from the core.

## Risks / Trade-offs

- [Newcomer expects a web app out of the box → the starter yields a CLI app] → the
  HTTP binding recipe is ~15 lines, executed under docs tests, and linked from the
  walkthrough's first page; the accepted cost of not choosing a transport for the
  user.
- [Resource recipe friction → users fall back to module globals] → accepted residual
  risk; recipe kept to a screenful, demonstrated twice (starter + storefront); revisit
  only with evidence, not speculation.
- [Config passthrough tempts future kernel-side validation] → Non-Goals and ADR-3 both
  say no; the seam is documentation, not code.
- [App table named like a future `[spoc]` sibling (e.g. `[spoc-x]`)] → only exact
  `spoc` is reserved; document that the kernel will never claim a second top-level
  table, making collision impossible by contract.
- [Binding recipes rot as their frameworks evolve] → the generated starter itself has
  no third-party dependencies to rot; recipes execute under the docs-tests policy, so
  a breaking upstream release fails loudly there, not in a generated project.
- [Vocabulary reads as mandatory → "you must have five kinds"] → docs phrase it as a
  default with the deviation rule stated in the same breath; `spoc init` continues to
  accept `--kinds`.

## Migration Plan

Additive only. No published-surface removals or renames; `apicheck` baseline gains the
new template-set entry and docs pages. Existing generated projects are unaffected
(`default` set unchanged; config passthrough is new data on `Config`, no existing field
changes meaning). Rollback is deleting the additions.

## Open Questions

None. The `/ai:decide` gate ran 2026-08-10; both decisions are approved and recorded in
the Decision blocks under ADR-3/ADR-5. Kind contribution stays deliberately closed
(ADR-4).
