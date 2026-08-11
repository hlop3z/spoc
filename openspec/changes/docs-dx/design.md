# docs-dx — design

## Context

A docs audit against the FastAPI bar scored the prose ~9 and the structure ~4. The
five gaps: no end-to-end tutorial demonstrating the north star, no task-oriented
how-to section, no visible payoff on the landing page, no error index, and — the
mechanical one — only a single doc snippet executed by the test suite despite the
stated "docs examples must run" bar. The docs site is MkDocs Material with
`macros`, `termynal`, `autorefs`, and `mkdocstrings` (griffe, `paths: [../src]`)
already configured in `docs/mkdocs.yml`. The shipped CLI's parser factory is
`spoc.cli._build_parser`. The existing docs-mirror tests live in
`tests/test_framework.py` and the example-is-the-fixture pattern
(`tests/test_examples.py`, `tests/test_scaffold_starter.py`) is the strongest thing
the current docs do — this change extends that pattern to the docs themselves.

Three build-vs-adopt decisions were gated through `/ai:decide` before this change
existed and are recorded in the root `DECISIONS.md` (this change was proposed after
the gate ran; the blocks live there rather than here — do not re-decide them):

- **Doc snippet execution — Adopt `pytest-examples`** (pydantic; discovery via
  `find_examples()`, expected-output insertion via `--update-examples`).
- **API member lists — Adopt (configure) mkdocstrings/griffe `__all__` derivation**
  (drop hand-enumerated `members:` lists; griffe treats `__all__` as authoritative).
- **CLI reference — Extend `mkdocs-macros` with a help-dump macro** (~20 lines
  importing the real parser factory; purpose-built plugins failed the maturity rubric).

## Goals / Non-Goals

**Goals:**

- Make documentation drift mechanically impossible for: snippet correctness, snippet
  output, API member listings, CLI reference, and error-index completeness.
- Demonstrate the north star: a tutorial that authors a dependency-free framework on
  the kernel, executed end-to-end by the test suite.
- Restructure navigation for task-orientation: a How-To group, a landing-page payoff,
  and nav order that matches the pages' own `Next:` chain.

**Non-Goals:**

- No changes to `src/spoc/` runtime code, the starter set, or any existing capability's
  requirements. (One permitted exception class: docstring-only edits if a rendered page
  needs them.)
- No new runtime dependencies — everything lands in the docs/dev dependency group;
  `dependencies = []` is untouched.
- No hosting, theming, or publishing changes.

## Structure and dependency direction

The docs content (`docs/docs/**/*.md`) is the core artifact; everything else adapts
to it, never the reverse:

- **Test-time adapter** — `tests/test_docs_examples.py`: discovers and executes doc
  snippets. The only module that imports the snippet-execution tool. Snippets needing
  a project tree get one from `spoc.testing` (the shipped harness), keeping the docs'
  files verbatim.
- **Build-time adapters** — `docs/main.py` (the mkdocs-macros default module) owns the
  CLI help-dump macro; `docs/mkdocs.yml` owns the mkdocstrings member-derivation
  options. Markdown pages contain only plain markdown plus macro placeholders.
- **Inward-only**: adapters import from `spoc`; nothing in `src/spoc/` knows the docs
  exist. The macro imports `spoc.cli._build_parser` — a private name, acceptable
  because the importer is dev-side build machinery, not a consumer; if the underscore
  ever bites, the fix is renaming the factory, not duplicating the parser.

## Decisions

### D1 — Tutorial shape: extract-from-the-page, stdlib transport

The tutorial (`docs/docs/learn/build-a-framework.md`, nav title "Build a Framework")
authors files under a `title="…"` fence per step — the docs' existing idiom — and the
test suite *extracts those fences* into a temp project tree in page order, boots it,
and asserts the final request/response. The page is the single source; there is no
second copy of the tutorial code in the test tree.

- Transport: stdlib `http.server` with a handler that projects
  `registry.by_kind("routes")` — keeps the framework-tutorial spec's dependency-free
  requirement and proves "SPOC sits below your HTTP framework" without picking one.
- Final payoff: an HTTP request (shown with `curl`, executed in-test with
  `urllib.request` against an ephemeral port) returning JSON derived from a
  registered component.
- Alternative considered: tutorial code as committed example files with a docs-mirror
  test (the `examples/` pattern). Rejected: two copies of the same code with a
  mirror test is exactly the drift class this change exists to close; extraction
  makes the page itself the fixture.

### D2 — Snippet policy: three states, none silent

Every Python fence under `docs/docs/**` is in exactly one state:

1. **Runnable standalone** — executed as-is.
2. **Runnable in a project tree** — the fence's `title` path places it into a
   harness-provided tree; the page's tree is assembled per-page in reading order.
3. **Explicitly non-runnable** — carries the adopted tool's native skip marker
   (verified at implementation; whatever form it takes, it must be visible in the
   markdown source). Counted and reported as skipped.

The audit's known-broken fragments (`index.md` missing imports/`BASE_DIR`,
`lifecycle.md` missing `import spoc`, the REPL-style attribute lists) get completed
into state 1/2 rather than marked state 3 wherever completing them is possible —
state 3 is for output-only and deliberately-partial illustrations, not for rot.

### D3 — Expected output via the adopted tool's update mode

Where a snippet's value is its printed result, the expected output is inserted and
maintained by the adopted tool's update mode (`--update-examples`), never typed by
hand. The gate runs in check mode; regeneration is a one-command mechanical step.
This supersedes hand-written output blocks; the two existing docs-mirror tests in
`tests/test_framework.py` that assert snippet behavior are folded into the new
module if redundant, kept if they pin behavior beyond execution (per-case call at
implementation, recorded in the task).

### D4 — Error index completeness is a test, not a tool

`docs/docs/api/errors.md` is a hand-written table (trigger → fix → concept link) —
the *prose* must be authored; only *completeness* is mechanical. A small test derives
the public exception set (members of `spoc.__all__` that are exception types) and
asserts each name appears in the page. No new dependency; it is one assertion over
two already-available facts.

### D5 — Navigation: one new group, one ordering fix, one payoff block

- New nav group **How-To** between Learn and Tools: one page per extracted recipe —
  database resource (from `vocabulary.md`), FastAPI/transport binding (from
  `starter.md`), settings validation (from `configuration.md`), testing your app
  (from `testing.md`'s harness content), shipping a reusable app (from `plugins.md`).
  Source pages keep the concept prose and link to the recipe; the code moves — it is
  not duplicated (single-source rule).
- Nav order aligns with the pages' `Next:` chain (`configuration.md` before
  `starter.md`, matching quick-start's outbound link).
- `index.md` gains a "See it work" block above the fold: the three commands and the
  real `--help` output already shown in `starter.md`, rendered with the installed
  `termynal` plugin. The output text is one of the executed snippets (state 2), so
  the landing page cannot show stale output.

### D6 — Member derivation stays inside existing config

`api/public.md` and `api/tooling.md` drop hand-listed `members:` blocks; each
`::: module` directive renders the module's `__all__`-derived exports. The global
handler options in `mkdocs.yml` (filters, ordering) remain the single home for
rendering policy. A docs-build in strict mode joins the validation gate so a
rendering regression (e.g. a module losing its `__all__`) fails loudly.

## Risks / Trade-offs

- [Extraction harness grows into a test framework] → Scope is fixed: place fences by
  `title`, run, assert; anything more (fixtures, mocking, parametrization) is a sign
  the page is too clever and the *page* gets simplified. The harness lives in one
  module beside its only consumer.
- [Tutorial's ephemeral-port HTTP test is flaky on CI] → Bind port 0, read the bound
  port, single request, close; no sleeps. Fallback if flake appears anyway: call the
  handler in-process without a socket and keep the `curl` block as a state-3 display.
- [`--update-examples` reformats snippets in a style that fights the docs' voice] →
  Formatting config is pinned in the test module; if the tool's formatter is too
  opinionated for a given block, that block presents output as a fenced text block
  (state 3) with the assertion done in-test instead.
- [Skip markers sprinkled as escape hatch] → The test module reports the skip count;
  the tasks set a ceiling (only output-only and deliberately-partial blocks), and
  review enforces it — new skips need a reason in the fence line.
- [mkdocs strict build breaks on unrelated warnings] → Introduce strict mode in this
  change while the page set is being touched anyway; fix what it surfaces here rather
  than deferring.

## Migration Plan

Docs-only: no deploy or rollback concerns beyond normal site publishing. Land
mechanically in two stages — (1) integrity machinery + snippet completion (existing
pages start failing loudly, then pass), (2) new content (tutorial, how-to, errors,
landing block) on top of the now-enforced rails.

## Open Questions

None blocking. The one deferred verification: the adopted snippet tool's native
skip-marker syntax and sequential-block behavior — verified in the first
implementation task, recorded in `tasks.md` alongside the D3 fold-in decisions.
