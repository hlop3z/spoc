# docs-dx

## Why

A docs audit against the best-in-class bar (FastAPI) found the prose strong but the
structure weak: the "a kid could build a framework with it" north star is asserted and
never demonstrated, task-oriented recipes exist but are buried inside concept pages, the
landing page shows no running payoff, and — despite the project's stated "docs examples
must run" bar — exactly one snippet is executed by the test suite, so every other page
can rot silently. Several fragments would fail today if run. The kernel is done and the
ecosystem can only grow with time; docs quality is the one adoption lever fully in our
control, and drift-proofing is the part that must be mechanical rather than aspirational.

## What Changes

- **A north-star tutorial**: a walkthrough that authors a small, runnable framework on
  the kernel line-by-line — declare kinds, write an app, project the registry onto a
  transport — ending with a real request served. The tutorial's accumulated code is
  executed by the test suite, so the page cannot describe a framework that doesn't work.
- **Executed doc snippets**: every Python code block under `docs/docs/**` either runs in
  CI or carries an explicit skip marker; fragments become complete files with expected
  output shown, in the docs' existing `title="…"` idiom.
- **API reference derived from source**: the hand-enumerated member lists in the API
  pages are replaced by listings derived from the package's declared public surface, so
  a new export cannot ship undocumented.
- **CLI reference derived from the parser**: the CLI page's command/flag documentation is
  generated from the real parser at docs build time instead of hand-written prose.
- **An error index**: one page mapping every public exception to what triggers it and the
  one-line fix, linked from the concept page that explains it.
- **A how-to section**: the recipes currently buried inside concept pages (resource
  wiring, transport binding, settings validation, testing an app, shipping a reusable
  app) are extracted into a task-oriented nav group, one page per "how do I X".
- **A landing-page payoff**: the starter's generated-CLI output moves above the fold on
  the landing page, showing a result — not just code — in the first screen.

## Capabilities

### New Capabilities

- `documentation-integrity`: the contract that documentation cannot drift from the code —
  doc snippets execute (or are explicitly marked non-runnable), API member listings and
  the CLI reference derive from the source of truth rather than hand-enumeration, and
  every public exception is covered by the error index. Realization involves build-vs-adopt
  decisions (snippet execution, reference derivation, CLI generation) — already gated and
  recorded via `/ai:decide` in `DECISIONS.md`.
- `framework-tutorial`: the end-to-end tutorial contract — the tutorial's code, assembled
  in the order the page presents it, boots on the kernel and serves a real request, and
  the test suite executes it.

### Modified Capabilities

None — no existing capability's requirements change. The how-to extraction, landing-page
payoff, and error-index pages are content and navigation work inside the existing docs
site; kernel behavior, the starter set, and the reference application are untouched.

## Impact

- **Docs**: `docs/docs/**` (new tutorial page, new how-to nav group, error index page,
  landing page edit, API/CLI pages switch to derived listings), `docs/mkdocs.yml` (nav,
  plugin configuration).
- **Tests**: a new docs-execution test module; the existing docs-mirror tests in
  `tests/test_framework.py` fold into or coexist with it.
- **Dependencies**: docs/dev dependency group only — the shipped package's
  `dependencies = []` invariant is untouched, and no `src/spoc/` code changes.
- **Not in scope**: new kernel features, starter-set changes, spec changes to existing
  capabilities, publishing or hosting changes.
