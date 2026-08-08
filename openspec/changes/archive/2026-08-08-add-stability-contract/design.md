## Context

SPOC is at 0.5.0 with `Development Status :: 4 - Beta` and an empty `dependencies` list.
The top-level `spoc` package re-exports 25 names; `spoc.formats`, `spoc.testing`,
`spoc.diagnostics`, and `spoc.scaffold` each publish their own `__all__`; and the artifact
additionally ships a console script, a `pytest11` entry point, five extras, a `spoc.toml`
schema, and a scaffold template contract. None of these carries a recorded tier.

Two constraints shape every decision below:

- **Zero runtime dependencies.** `dependencies = []` is load-bearing. Nothing this change
  adds may enter the base install.
- **The contract must not become part of the surface it describes.** Anything shipped
  inside `src/spoc/` to enforce the contract would itself need a tier, and would need to be
  covered by its own check. The enforcement mechanism therefore lives outside the package.

## Goals / Non-Goals

**Goals:**

- One machine-readable source of truth for every element's tier, from which every other
  view (docs, warnings, the check) is projected rather than restated.
- A drift check runnable against the working tree, in the same gate as the rest of
  `.canon/checks.md`.
- A once-only audit that resolves `spoc.core`'s ambiguous status by decision, not by
  leaving the current hedge in the module docstring.

**Non-Goals:**

- Cutting 1.0. This change publishes the criteria; meeting them is later work.
- Adding back-compat shims for anything that has already changed. The pre-stable allowance
  is explicitly preserved — this change ends the *absence* of a policy, not the freedom to
  break before 1.0.
- A runtime API for querying tiers. Consumers read documentation; tooling reads the
  manifest at development time. Shipping a query API would grow the surface to describe
  the surface.

## Decisions

### The contract is data, and every other view is a projection of it

Tier assignments live in `[tool.spoc.stability]` in `pyproject.toml`: one array per tier,
plus the enumerated exclusions. This is data in its native format, read through an adapter
— not a dict literal in code.

*Why `pyproject.toml` over a new `stability.toml`:* it is already the distribution
metadata's home, already TOML, already read by the stdlib with no dependency, and already
ships in the sdist. A new file would be a second place to forget.

*Why one source with projections rather than markers in code:* the specs require both that
a tier be visible at the point of definition and that the declared surface be verifiable.
Satisfying both with two hand-maintained sources guarantees drift. Instead the manifest is
authoritative, and the check enforces that each `provisional` element's own documentation
carries the warning text. The docstring is a checked projection, never a second truth.
This is the same shape the kernel already uses — one registry, many projections.

### The checker is a project tool, not a package feature

The drift check lives in `scripts/py/` as a CLI utility (the `/ai:tool` path), not in
`src/spoc/`. It is development-time tooling: shipping it would add surface, pull a
dev dependency toward the base install, and create the recursion of a public API that
polices the public API.

Structure follows Rule 2 — pure core, adapters at the edges:

- **Core (pure):** given a declared manifest and an observed surface, produce a diff —
  undeclared elements, declared-but-absent elements, and unmarked `provisional` elements.
  No I/O, no introspection.
- **Adapters:** a TOML reader for the manifest; a surface extractor for the observed side;
  a reporter for output.
- **Entry point:** argument parsing and exit code only.

Dependencies point inward: the diff core knows nothing about TOML, about the extraction
tool, or about the terminal.

### Surface extraction is adopted, not written

Determining a Python package's true public API — re-exports, `__all__` precedence,
inherited members, conditional imports, signature changes — is a solved problem, and this
repo has already paid a day for hand-rolling a solved problem once. Griffe is adopted as a
development dependency (see the ADR below).

Griffe covers the *import* surface only; it documents that it cannot check CLI options,
entry points, or extras. Those elements are therefore checked by thin complements of our
own — `importlib.metadata` for entry points, the `pyproject.toml` reader for extras — feeding
the same diff core. The split is deliberate: adopt the hard part, hand-write only what no
tool covers.

### The deprecation signal follows PEP 702

`@deprecated` is the standard for marking a deprecated element, and it satisfies the
release-policy requirement on its own: it raises `DeprecationWarning` at runtime (so it is
suppressible and escalatable through the normal warning filters) and is visible to type
checkers statically.

It is stdlib as `warnings.deprecated` only from 3.13, while `requires-python` is `>=3.12`.
The gap is bridged by a fallback shim behind a single adapter, not by taking a runtime
dependency — `dependencies = []` holds. On 3.13+ the shim resolves to the stdlib decorator
itself, so the fallback path deletes itself the day `requires-python` moves to `>=3.13`.

### `spoc.core` is Internal, and promotion requires a present use case

The module docstring's current hedge — reachable "for anyone extending the kernel" —
is replaced by a decision: `spoc.core` is `internal`.

The audit rule is deliberately strict: a `spoc.core` name is promoted to a public location
only if a concrete extension use case needs it *today*. Speculative promotion is how a
surface becomes unbreakable by accident. The reference application and the scaffold
templates are the evidence base for "needed today" — they are the only in-repo consumers
that stand in for a downstream framework.

### Tier vocabulary is fixed at three

`public` / `provisional` / `internal`, closed. A fourth tier ("experimental",
"deprecated-but-present") would encode lifecycle state, which the release policy already
tracks through the deprecation lifecycle. Deprecation is a state a `public` element is in,
not a tier it moves to.

## Decisions (ADRs)

### Decision: Public API surface extraction and drift detection — Adopt `griffe`

- **Status**: approved
- **Why**: the only option that serves both specs — extraction feeds the drift check, and
  `griffe check` classifies breaking vs compatible changes between refs, which
  `release-policy` needs to assert version increments. ISC, actively maintained, and its
  public-API rules (`__all__` precedence, underscore convention, imports not public unless
  redundantly aliased) already match ours. Development dependency only.
- **Considered**: *Build on stdlib* (`importlib`/`inspect`/`ast`) — re-implements
  `__all__` precedence, re-export resolution and signature diffing, and yields no breakage
  classification. *Snapshot-test the surface* — cheap and does catch drift, but reports
  only that something changed, never what kind, so it cannot support the compatibility
  assertions.
- **Isolation**: the surface-extractor adapter. The diff core receives an extracted
  surface and knows nothing about griffe; replacing it is a one-file change. Griffe's
  documented blind spots (CLI options, entry points, extras) are covered by sibling
  adapters feeding the same core.

### Decision: Deprecation marking and runtime signal — Extend PEP 702 (`warnings.deprecated` + shim)

- **Status**: approved
- **Why**: PEP 702 is the standard and satisfies the release-policy requirement outright —
  a `DeprecationWarning` that consumers can suppress or escalate, plus static
  type-checker visibility. It is stdlib only from 3.13 while `requires-python` is `>=3.12`,
  so a small fallback bridges the gap; on 3.13+ the stdlib decorator is used unchanged.
- **Considered**: *Adopt stdlib directly by bumping `requires-python` to `>=3.13`* —
  strictly cleaner, but dropping 3.12 is a scope change requiring the proposal and specs to
  change, not just this ADR. *Adopt `typing_extensions`* — the canonical backport, but a
  runtime dependency, which `dependencies = []` rejects outright.
- **Isolation**: one deprecation adapter owning the import fallback. Call sites use the
  decorator; nothing else observes which implementation supplied it.

### Decision: Manifest parsing — Adopt stdlib `tomllib`

- **Status**: approved
- **Why**: standard-format parsing is never hand-rolled, so the question was only which
  parser. `tomllib` is stdlib, reads the file the manifest already lives in, and costs
  nothing against `dependencies = []`. The checker only reads, so the absence of a stdlib
  TOML *writer* is irrelevant here.
- **Considered**: the project's own `spoc.formats` codecs — rejected, since the checker
  must not import the package whose surface it is auditing.
- **Isolation**: the manifest-reader adapter.

## Risks / Trade-offs

- **The manifest drifts from reality between checks** → the check runs in
  `.canon/checks.md`, the same gate as tests and lint, so drift fails before it lands
  rather than at release time.
- **Committing too early to a surface that is still moving** → the `provisional` tier
  exists for exactly this, and the pre-stable allowance means a wrong call is correctable
  in a minor release. The cost of a premature `public` is bounded until 1.0.
- **The 1.0 criteria require the deprecation lifecycle to be *exercised*, not just
  documented** → this is intentional friction: a lifecycle first run during the 1.0
  release is a lifecycle discovered to be broken during the 1.0 release. It does mean at
  least one real deprecation must pass through the machinery beforehand.
- **`pyproject.toml` grows** → the manifest is arrays of strings, and keeping it beside
  the classifier and extras it constrains is worth more than a shorter file. Revisit only
  if it becomes the majority of the file.
- **An adopted extractor becomes unmaintained** → it sits behind one adapter with a pure
  core on the other side; replacing it is a single-file change, which is the point of
  putting the boundary there.
- **The policy reversal reads as a promise to existing 0.3.x/0.5.0 users** → the changelog
  entry must state plainly that the contract takes effect going forward and grants nothing
  retroactively.

## Migration Plan

1. Publish the contract and policy; the manifest and check land together so the contract
   is enforced from its first commit.
2. `CHANGELOG.md` records that this supersedes the 0.5.0 "no migration path, none planned"
   stance, effective for subsequent releases only.
3. The pre-stable allowance remains in force. The next release is a minor; no behavior is
   removed by this change.

Rollback is deletion of the manifest, the tool, and the docs page — no runtime code
depends on any of them.

## Open Questions

- Does the `spoc.toml` schema warrant its own versioning field, separate from the package
  version? Deferred: it is `public` under this contract either way, and adding a schema
  version is only justified once a second schema shape exists.
- Should the scaffold template contract be `provisional` rather than `public`? It is the
  youngest surface and the remote-template work is recent. Resolve during the audit task
  with the same "needed today" evidence rule.
