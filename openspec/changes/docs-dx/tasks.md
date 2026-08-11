# docs-dx — tasks

Stage 1 (groups 1–3) lands the integrity rails; stage 2 (groups 4–7) builds the new
content on top of them. Group 8 closes out.

## 1. Snippet-execution machinery (rails first)

- [x] 1.1 Add `pytest-examples` to the docs/dev dependency group; verify its native
      skip-marker syntax and sequential-block behavior against the installed version
      and record both in a comment at the top of the new test module (design Open
      Question — resolve here, first). Resolved: `test="skip"` fence setting via
      `prefix_settings()` (consumer-honored, as pydantic's docs do); no sequential
      state between fences — pages needing accumulation use titled project files.
      Dependency landed in `dev` (the test suite imports it, the docs build doesn't).
- [x] 1.2 Create `tests/test_docs_examples.py`: discover every Python fence under
      `docs/docs/**/*.md` via `find_examples()`, execute state-1 snippets, and fail
      with the source file named for any unmarked non-running snippet
- [x] 1.3 Add the project-tree path (state 2): fences whose `title` is a project path
      are placed verbatim into a per-page tree, in reading order, and the page's
      `title="main.py"` entry runs as a subprocess (verbatim files beat re-derived
      `ProjectTree` structure — the spec's "same files, same order" wins over the
      design's harness wording)
- [x] 1.4 Wire the skip accounting: state-3 snippets are counted and reported;
      `SKIP_CEILING` (starts 0) makes raising the count a visible, reviewable diff
- [x] 1.5 Run the suite; it MUST fail at this point on the known-broken fragments
      (`index.md`, `lifecycle.md`, REPL-style lists) — commit the machinery only once
      it demonstrably catches them. Verified: 31 failed / 9 passed, all audit-known
      fragments among the failures. One local patch: `EvalExample._write_file` lacks
      an encoding (Windows mojibake) — pinned UTF-8 via fixture, upstream-PR worthy.

## 2. Existing snippets brought to green

- [x] 2.1 Complete the broken fragments into runnable state: imports and `BASE_DIR` on
      `index.md`, `import spoc` on `lifecycle.md`, REPL-style attribute lists in
      `names-and-registry.md` and `configuration.md` become executable code with
      verified output. Ten pages became project pages (quick-start, index,
      configuration, lifecycle, names-and-registry, vocabulary, plugins, formats,
      testing) — each declares its files with `title=` and runs via `main.py`
- [x] 2.2 Decorator-naming drift resolved: the pages were each faithful to their own
      source — templates generate plural (`models = framework.kind("models")`), the
      storefront example uses singular (`view`). Docs keep plural (the template
      convention readers generate); `apps.md`'s storefront fence is now
      build-time-included from `examples/apps/orders/views.py` with a sentence naming
      the difference. FLAGGED out of scope (Rule 7): the residual divergence is
      between `examples/framework.py` and the templates themselves
- [x] 2.3 Expected-output blocks: `#> ` comments on the one printing standalone
      snippet (parse/compose). CAUTION recorded in the test module: 0.0.18's
      `--update-examples` writer corrupts pages on CRLF checkouts — verified; use an
      LF checkout or copy the check-mode diff by hand
- [x] 2.4 Fold-in decision, per case: BOTH KEPT. `test_settings_seam_docs_example_runs`
      is the only executor of the pydantic seam (the page's pydantic `main.py` version
      is overwritten before the tree runs); `test_resource_lifecycle_recipe_…` asserts
      post-shutdown refusal the page project doesn't reach
- [x] 2.5 Full docs snippet suite green: 22 passed, 5 skipped (+2 titled skips),
      ledger 7/7 — zero unmarked

## 3. Derived references (API, CLI, errors completeness)

- [x] 3.1 Hand-enumerated `members:` lists dropped from both API pages; each
      `::: module` directive now renders its `__all__`-derived exports (verified:
      `MetadataContractError` on public, `PointerResolutionError` on tooling).
      `spoc.formats.errors`' separate block collapsed into `::: spoc.formats` — its
      `__all__` already exports the error types
- [x] 3.2 `cli_help()` macro added to the existing `docs/main.py` (it already existed
      with three macros — extended, not created). Deviation from design D-wording:
      the macro shells out to `python -m spoc.cli … --help` instead of importing
      `_build_parser` — same parser, no private-attribute walking to reach subcommand
      parsers. `tools/cli.md`: overview block, init options table, and check flags
      are now `{{ cli_help(...) }}` placeholders
- [x] 3.3 Strict mode wired as `task docs:check` in all three homes (checks.md row,
      Taskfile `check` list, ci.yml `docs-build` job). It surfaced one real defect:
      `pymdownx.snippets` was silently dropping the storefront include —
      `base_path`/`check_paths` now configured so a broken include fails the build
- [x] 3.4 Error-index completeness test in `tests/test_docs_examples.py` — every
      exception type in `spoc.__all__` must have a backticked row in
      `docs/docs/api/errors.md`; landed together with the page (5.1)

## 4. The north-star tutorial

- [x] 4.1 `learn/build-a-framework.md` written: empty folder → four files (rules,
      app, settings, stdlib `http.server` surface) → `curl` returns JSON; section 7
      adds a function and the endpoint appears with no route table edited. The
      port comes from argv so the test can pass 0
- [x] 4.2 `test_framework_tutorial`: assembles the page's files in page order, boots
      on an ephemeral port (argv `0`, reads the printed bound-port line — no
      sleeps), asserts both curl payloads exactly as displayed. The page is excluded
      from the generic run-`main.py` test since its entry serves forever. The test
      caught a payload mismatch in my own page draft before it ever shipped
- [x] 4.3 Nav (Learn, after Plugins), `plugins.md` `Next:` re-pointed, and the
      landing page's north-star claim now links the tutorial

## 5. Error index

- [x] 5.1 `docs/docs/api/errors.md` written: 17 rows across five concern groups —
      trigger, fix, concept-page link each; formats' own error family pointed at
      `FormatError` in the toolbox reference
- [x] 5.2 Completeness test passing (23 passed total) and in the gate via the Unit
      tests row; page in nav under API Reference before Stability

## 6. How-To section

- [x] 6.1 Five how-to pages: add-a-database (from `vocabulary.md`), bind-a-transport
      (from `starter.md`, rebuilt over the tutorial's project), validate-settings
      (from `configuration.md`), test-your-app (from `testing.md`'s fixture
      example), ship-a-reusable-app (the `spoc.component` marker recipe). Code
      moved; each source page keeps the reasons plus a link
- [x] 6.2 All five are executed project pages (the transport page proves the FastAPI
      route table without a server — `app.routes` — so no httpx/TestClient
      dependency is needed); starter's skip-marked recipe fence deleted, ceiling
      7 → 6
- [x] 6.3 How-To nav group between Learn and Tools; how-to pages chain `Next:`
      internally and exit to the CLI page; `configuration.md`'s `Next:` re-pointed
      to starter
- [x] 6.4 Nav order aligned: Settings File before Starter, matching quick-start's
      outbound link

## 7. Landing-page payoff

- [x] 7.1 "See it work" block above the fold (termynal-marked): pip install → init
      → real `--help` output. Verification is stronger than the planned state-2
      snippet: `test_displayed_starter_help_is_real` generates the actual starter
      and diffs its output against the block on BOTH pages that display it — and
      immediately caught that both pages were abridging the real output (missing
      `options:` section); fixed
- [x] 7.2 `pip install spoc` is now the block's first line, on the page itself

## 8. Close-out

- [x] 8.1 Full `task check` green: formatter, linter, types, 680-test suite (30 docs
      tests), Go build, doc links, strict docs build, apicheck 0 fatal, apidiff 0
      breakages
- [x] 8.2 `CONTRIBUTING.md` gains "Editing the docs? The snippets are tested" —
      the three states, the LF-only regeneration caveat, and the derived-listing
      warning
- [x] 8.3 `CHANGELOG.md` Unreleased leads with the docs-integrity entry;
      `docs/architecture/docs-integrity.md` added (Rule 1): the three snippet
      states and the derived-vs-test-held split
