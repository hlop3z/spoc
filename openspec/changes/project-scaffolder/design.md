## Context

The kernel discovers apps from `spoc.toml`, loads each app's modules in dependency order, and
registers every marked object. None of those conventions are enforced at authoring time — they
are enforced at `start()`. The scaffolder's job is to move that agreement from "the author
maintained it by hand" to "it was emitted consistent and a test proves it stays that way."

Three constraints shape everything below:

1. **`dependencies = []` is an invariant of the published package.** Whatever the scaffolder
   needs must be acquired only by users who opt in, and the kernel must never import it.
2. **Scaffolding is a solved problem elsewhere.** The canon's rebuild precedent (`loc` vs
   `tokei`) applies to this change more directly than to any other in the repo. Nothing here is
   implemented until `/ai:decide` has run.
3. **The kernel does not know where the framework declaration lives.** `spoc.toml` names apps
   and plugins; the `Framework(...)` object is constructed in a module the *user* imports and
   hands to `start(BASE_DIR)`. Adding an app needs that object's kinds, and today nothing on
   disk points at it.

## Goals / Non-Goals

**Goals:**

- One command yields a project that starts unedited; a second adds an app to an existing one.
- The emitted shape is data, replaceable by a downstream framework without forking anything.
- Every failure mode is a refusal before the first byte is written.
- The kernel's install footprint is bit-for-bit unchanged.

**Non-Goals:**

- Not a general project generator. It emits spoc projects, not arbitrary Python packages.
- Not a migration tool. It does not upgrade or rewrite an existing project's layout.
- Not an interactive wizard in this change. Prompt-driven flows are a later concern; the first
  surface is non-interactive and scriptable.
- No kernel behavior changes. If the scaffolder needs something the kernel does not expose,
  that is a separate proposal, not a quiet addition here.

## Decisions

### D1 — Core computes a plan; adapters perform I/O

The core is pure: it resolves a template set, validates names, and returns an immutable
**generation plan** — an ordered set of (relative path, byte content) pairs plus the config
edits an operation implies. It touches no filesystem and imports nothing external.

This is what makes the spec's "nothing is written on failure" requirement structural rather
than aspirational: the whole plan is computed and validated first, and a plan that cannot be
fully realized is never handed to a writer. Conflict detection is a comparison between the plan
and a directory listing — itself a pure function over a listing the adapter supplies.

Ports: `TemplateSource` (yields template set data), `ProjectSink` (writes a plan, lists
existing paths). Adapters implement both. Dependency direction is inward only; the core names
the ports, the adapters depend on the core.

### D2 — The CLI is a thin adapter over the plan

The command surface translates arguments into a core call and renders the result. It holds no
generation logic, no conflict rules, and no template knowledge, so the same operations are
invocable from a downstream framework's own entry point without going through argv. This is
what lets zmag expose `zmag-init` as a one-line adapter rather than a reimplementation.

### D3 — Template sets are directories of native-format files

A template set is a directory tree of files carrying the format they will be emitted as, plus
one manifest declaring the substitution values the set depends on. Content is never a string
literal in program code (canon: data is not code).

Template files take a suffix marking them as templates rather than being valid source in place
— otherwise the repo's own linter and type checker would try to analyze half-written modules
containing placeholders. The suffix is stripped on emit. Trade-off accepted: template files are
not directly runnable, which is why D6 exists.

### D4 — Kinds for "add app" come from the declaration, via a scaffolder-side convention

`add app` must emit one module per kind that the *target project's* framework declares. The
kinds live in the `Framework(...)` call, which nothing on disk points at.

Chosen: the scaffolder resolves the declaration by its own documented convention (the module
path it generated in the first place), overridable by an explicit argument. The convention
belongs to the scaffolder, not the kernel.

Rejected: recording the kinds in `spoc.toml`. It is the more discoverable option, but it makes
the kind set exist in two places that can disagree — exactly the drift this change is meant to
end — and it would turn a purely additive change into a modification of the
`project-configuration` capability.

Deferred to an open question: whether resolving that convention should *import* the module
(reusing the kernel's own importer, consistent with how `start()` already treats user code) or
read it without execution. Importing is simpler and matches kernel behavior; not importing is
safer for a tool that runs against a project the user may have just cloned.

### D5 — Build-vs-adopt: three concerns, all pending `/ai:decide`

Per the canon these are not decided here. Recorded with a leaning only, to be confirmed,
overturned, and written up as ADRs by `/ai:decide` before any implementation task starts:

| Concern | Leaning | Note |
| ------- | ------- | ---- |
| Project generation / template rendering | **Adopt** | Mature dedicated tools exist for exactly this (copier, cookiecutter are the obvious candidates to evaluate). Building a renderer is the `loc`-vs-`tokei` mistake in a new costume. The rubric question is whether their project model fits emitting *into* an existing project (the `add app` case), which is where generic scaffolders are typically weakest. |
| Command-line surface | **Adopt** | `DECISIONS.md` already records cyclopts as this project's Python CLI framework. The decision is not automatic here, because that ADR governed workshop tools with no distribution constraint, and this surface ships to users — dependency weight now counts. Re-run the rubric rather than inherit the answer. |
| Filesystem write safety | **Build (thin)** | Correctness-sensitive, but the requirement is narrow: stage, verify, commit, and never traverse outside the target. Adopting a library for this is likely more surface than the problem. Confirm against what the chosen generator already guarantees — if it stages atomically, this concern collapses into the row above. |

### D6 — The generated project is tested by starting it

The spec's first scenario ("generated project starts unedited") becomes a real test: generate
into a temporary directory, start the framework against it, assert the registry contents, shut
down. This is the only mechanism that keeps templates honest as the kernel evolves — a kernel
change that would break new projects fails the kernel's own suite instead of reaching users.

### D7 — Distribution is an optional extra

The scaffolder ships in the same distribution behind an opt-in extra with its own console entry
point. `dependencies = []` stays literally unchanged. The kernel imports nothing from the
scaffolder package; the dependency runs one way, which a test asserts.

Rejected: a separate distribution. It is the cleaner isolation, but it doubles the release
process for a pre-1.0 project and makes the version relationship between kernel and scaffolder
something users have to reason about.

## Risks / Trade-offs

- **An adopted generator may not support emitting into an existing project.** → This is the
  decisive rubric criterion for `/ai:decide`, not a detail to discover during implementation.
  If no mature tool covers `add app`, the honest outcome is adopt-for-`init` and build the
  narrow in-place path, recorded as such.
- **Templates drift from the kernel as it evolves.** → D6. Drift becomes a failing test in this
  repo rather than a broken project in someone else's.
- **The scaffolder becomes a second definition of the project layout.** → It consumes the
  documented conventions; where it needs one the kernel does not define (D4), that convention
  is explicitly the scaffolder's own and is documented as such rather than implied.
- **An optional extra that users do not discover.** → The getting-started path leads with it,
  and the failure mode is benign: hand-assembly still works exactly as it does today.
- **Resolving the declaration by importing runs user code.** → Open question below; if
  importing is chosen it must be an explicit, documented behavior of the command, not a
  side effect users meet by surprise.

## Migration Plan

Purely additive; nothing to migrate. Existing projects are unaffected and hand-assembly remains
valid. Downstream, zmag's broken `zmag-init` entry point can be replaced by an adapter over the
core operations plus its own template set — a deletion, not a port.

## Open Questions

1. **Does resolving the framework declaration import it?** (D4) Decide before implementing
   `add app`. It is a user-visible safety property, not an implementation detail.
2. **Does `init` generate one app or none?** The spec requires the generated project to start
   with at least one registered component, which implies one. Confirm that an empty project is
   not the more useful default for someone adding their own app immediately.
3. **How is a downstream template set referenced** — by installed entry point, by path, or
   both? The spec requires resolution failures to list candidates, which is cheap for entry
   points and meaningless for arbitrary paths.
