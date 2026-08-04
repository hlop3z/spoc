## Context

The kernel discovers apps from `spoc.toml`, loads each app's modules in dependency order, and
registers every marked object. None of those conventions are enforced at authoring time — they
are enforced at `start()`. The scaffolder's job is to move that agreement from "the author
maintained it by hand" to "it was emitted consistent and a test proves it stays that way."

Two constraints shape everything below:

1. **`dependencies = []` is an invariant of the published package.** Whatever the scaffolder
   needs must not reach an installer of the kernel.
2. **Scaffolding is a solved problem elsewhere.** The canon's rebuild precedent (`loc` vs
   `tokei`) applies here, and the decisions in D5 were made against current research rather
   than assumed.

**Scope was narrowed during `/ai:decide`.** The change originally carried a second operation,
`add app`, which emitted into an existing project. It is dropped. That single cut removed the
design's hardest open question (discovering a target project's declared kinds, which required
either importing user code or inventing a convention the kernel does not have) and removed the
need to *edit* a configuration file at all — emitting a fresh one is plain text substitution.
A spoc app is `__init__.py` plus one near-empty module per kind; once `init` has produced a
working example, the second app is a copy-paste, and a surface must earn its complexity.

## Goals / Non-Goals

**Goals:**

- One command yields a project that starts unedited.
- The emitted shape is data, replaceable by a downstream framework without forking anything.
- Every failure mode is a refusal before the first byte is written.
- The kernel's install footprint is bit-for-bit unchanged.

**Non-Goals:**

- **No `add app` command.** Dropped deliberately (see Context).
- Not a general project generator. It emits spoc projects, not arbitrary Python packages.
- Not a migration tool. It does not upgrade, re-apply to, or rewrite an existing project.
- Not an interactive wizard. The surface is non-interactive and scriptable.
- No kernel behavior changes. If the scaffolder needs something the kernel does not expose,
  that is a separate proposal, not a quiet addition here.

## Decisions

### D1 — Core computes a plan; adapters perform I/O

The core is pure: it resolves a template set, validates names, and returns an immutable
**generation plan** — an ordered set of (relative path, content) pairs. It touches no
filesystem and imports nothing external.

This makes the spec's "nothing is written on failure" requirement structural rather than
aspirational: the whole plan is computed and validated first, and a plan that cannot be fully
realized is never handed to a writer. Conflict detection is a pure comparison between the plan
and a directory listing the adapter supplies.

Ports: `TemplateSource` (yields template set data), `ProjectSink` (writes a plan, lists
existing paths). Dependency direction is inward only; the core names the ports, the adapters
depend on the core.

### D2 — The CLI is a thin adapter over the plan

The command surface translates arguments into a core call and renders the result. It holds no
generation logic, no conflict rules, and no template knowledge, so the same operation is
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

### D4 — (withdrawn)

This slot held the mechanism for discovering a target project's declared kinds, needed only by
`add app`. With that operation dropped, `init` knows the kinds because it is the thing choosing
them. Retained as a numbered stub so the decision references in `tasks.md` and `HANDOFF.md`
stay stable.

### D5 — Build-vs-adopt outcomes

Researched and decided during `/ai:decide`. The findings that drove them:

- Cookiecutter renders a template directory to a *different* output directory by design and
  cannot render in place — irrelevant now that `add app` is gone, but it was the original
  reason to doubt a wholesale adopt.
- Jinja2 (which both copier and cookiecutter carry) *evaluates expressions*. The
  `scaffold-templates` spec requires substitution values to be "a declared, enumerable set
  rather than arbitrary evaluation" and requires template content not to be executed. Adopting
  Jinja means writing rules to restrict it; `string.Template` is that restriction by
  construction, and `Template.get_identifiers()` (3.11+) satisfies "declared values are
  enumerable" in one call.
- Requiring users to install a separate generator adds friction at exactly the moment the
  change exists to remove it. `spoc init` immediately after installing spoc is the shortest
  possible path.
- Django's `TemplateCommand` is the precedent: it backs `startproject` with no external
  templating dependency.

#### Decision: Project generation and template rendering — Build (thin) on the standard library

- **Status**: approved
- **Why**: `string.Template` matches the spec's no-evaluation requirement by construction where
  Jinja would have to be constrained into it, and adopting a generator would add an install
  step to the one command whose whole purpose is removing friction.
- **Considered**: Adopt copier (strong at new-project generation, and its `update` feature is
  real — but a Jinja dependency plus a separate install for a once-per-project command);
  adopt cookiecutter (the incumbent, but no in-place rendering and a weaker maintenance story
  than copier for the same cost).
- **Isolation**: `TemplateSource` port. The renderer is called from one adapter; swapping to
  Jinja later changes that adapter and nothing in the core.

#### Decision: Command-line surface — Adopt the standard library (`argparse`)

- **Status**: approved
- **Why**: Zero dependencies, so the scaffolder ships in the main package with
  `dependencies = []` untouched, and one command with a handful of flags is squarely inside
  what argparse does well.
- **Considered**: cyclopts (this project's recorded choice for *workshop* tools, where nothing
  ships to users — that ADR does not transfer, because dependency weight now counts against a
  stated invariant); typer (same objection, plus a heavier tree).
- **Isolation**: the CLI entry-point module only. It parses and renders; the core operation is
  callable without it.
- **Note**: the existing `DECISIONS.md` entry rejecting stdlib `flag` was about **Go**, whose
  `flag` package has no subcommands. Python's `argparse` has subparsers, required arguments,
  and short/long pairing. That rejection does not carry over.

#### Decision: Filesystem write safety — Build (thin) on standard-library primitives

- **Status**: approved
- **Why**: The requirement is narrow — stage, verify, commit, never traverse outside the target
  — and `tempfile` plus `os.replace` (atomic within a filesystem) plus
  `Path.resolve().is_relative_to()` are the adopted, well-tested primitives underneath it.
  A library here would be more surface than the problem.
- **Considered**: delegating staging to an adopted generator (collapses into the row above, and
  was rejected with it); a filesystem-transaction library (none mature enough to outweigh ~40
  lines of stdlib).
- **Isolation**: `ProjectSink` adapter.

#### Decision: Configuration file writing — resolved by scope, no dependency needed

- **Status**: approved
- **Why**: Stdlib `tomllib` is read-only, and comment-preserving edits need `tomlkit` — but
  only when *editing* an existing file. `init` emits a fresh `spoc.toml` from a template, which
  is plain text substitution. Dropping `add app` removed this concern rather than solving it.
- **Considered**: adopt tomlkit (correct had `add app` survived — round-trip editing is on the
  canon's never-hand-roll list, so this was the only acceptable way to keep that operation);
  hand-rolled TOML editing (rejected outright: standard-format serialization is mandatory-adopt).
- **Isolation**: n/a — the kernel's existing `tomllib` read path is untouched.

### D6 — The generated project is tested by starting it

The spec's first scenario ("generated project starts unedited") becomes a real test: generate
into a temporary directory, start the framework against it, assert the registry contents, shut
down. This is the only mechanism that keeps templates honest as the kernel evolves — a kernel
change that would break new projects fails the kernel's own suite instead of reaching users.

### D7 — Ships in the main package; no optional extra

Because every decision in D5 landed on the standard library, the scaffolder adds no
dependency. It ships in the same distribution with a console entry point, and
`dependencies = []` stays literally unchanged.

This supersedes the original plan for an opt-in extra, which existed only to quarantine
dependencies that no longer exist. The kernel still imports nothing from the scaffolder
package — the dependency runs one way, which a test asserts, so the scaffolder can be deleted
without touching the kernel.

## Risks / Trade-offs

- **`string.Template` is deliberately weak.** No conditionals, no loops. A template set needing
  "include this file only when X" cannot express it. → Accepted: the emitted shape is a fixed
  small tree. If a downstream set genuinely needs branching, that is the trigger to revisit the
  D5 generation decision, not to smuggle logic into the manifest.
- **Templates drift from the kernel as it evolves.** → D6. Drift becomes a failing test in this
  repo rather than a broken project in someone else's.
- **Users who want a second app get no help.** → Accepted, and the reason the cut is safe:
  `init` emits a working app that serves as the copy-paste source. If this proves wrong in
  practice, `add app` returns as its own proposal with D4 reopened honestly.
- **The scaffolder becomes a second definition of the project layout.** → It consumes the
  documented conventions and is tested by starting what it emits (D6), so a divergence fails
  the suite.

## Migration Plan

Purely additive; nothing to migrate. Existing projects are unaffected and hand-assembly remains
valid. Downstream, zmag's broken `zmag-init` entry point can be replaced by an adapter over the
core operation plus its own template set — a deletion, not a port.

## Open Questions

All resolved during `/ai:decide`:

1. ~~Does resolving the framework declaration import it?~~ Moot — `add app` was the only
   operation that needed to, and it is gone.
2. ~~Does `init` generate one app or none?~~ **One.** The spec requires the generated project
   to start with at least one registered component, and with `add app` dropped, that app is
   also the worked example a user copies for their second.
3. ~~How is a downstream template set referenced?~~ **By installed entry point.** The spec
   requires resolution failures to list candidates, which is cheap for entry points and
   meaningless for arbitrary paths.
