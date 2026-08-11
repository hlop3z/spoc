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

- [ ] 3.1 Drop hand-enumerated `members:` lists from `api/public.md` and
      `api/tooling.md`; let each `::: module` directive render `__all__`-derived
      exports; confirm the rendered member set matches the pre-change pages except
      for intended corrections
- [ ] 3.2 Create `docs/main.py` with the CLI help-dump macro over
      `spoc.cli._build_parser`; replace `tools/cli.md` hand-written command/flag prose
      with macro placeholders (keep the page's tutorial prose)
- [ ] 3.3 Turn on mkdocs strict mode for the docs build in the validation gate; fix
      whatever it surfaces in the existing pages
- [ ] 3.4 Add the error-index completeness test: every exception type in
      `spoc.__all__` must appear in `docs/docs/api/errors.md` (page authored in 5.1 —
      test lands first and fails until then, or lands with the page; either way it is
      in the gate by the end of group 5)

## 4. The north-star tutorial

- [ ] 4.1 Write `docs/docs/learn/build-a-framework.md`: from empty directory to a
      dependency-free framework — declare kinds, author one app component, project
      the registry onto stdlib `http.server`, end with the real `curl` invocation and
      its JSON response (design D1)
- [ ] 4.2 Add the extraction test: assemble the page's `title`-fenced files in page
      order into a temp tree, boot on an ephemeral port (bind 0, read port, single
      request, no sleeps), assert the exact response the page displays
- [ ] 4.3 Add the tutorial to nav (Learn group, after `plugins.md`) and to the
      pages' `Next:` chain; link it from `index.md`'s north-star claim

## 5. Error index

- [ ] 5.1 Write `docs/docs/api/errors.md`: one row per public exception — trigger,
      one-line fix, link to the concept page; reuse the real error text already shown
      in `names-and-registry.md` and friends
- [ ] 5.2 Confirm the 3.4 completeness test passes and is running in the gate;
      add the page to nav under API Reference

## 6. How-To section

- [ ] 6.1 Extract the recipes into `docs/docs/how-to/` — one page each: database
      resource (from `vocabulary.md`), transport binding (from `starter.md`),
      settings validation (from `configuration.md`), testing your app, shipping a
      reusable app; code moves, source pages keep prose + a link (design D5, no
      duplication)
- [ ] 6.2 Each recipe page's snippets are state 1 or 2 (executed); the FastAPI
      binding runs under the `examples` dependency group as it does today
- [ ] 6.3 Add the How-To nav group between Learn and Tools; re-point every `Next:`
      link affected by the move
- [ ] 6.4 Align nav order with the reading chain: `configuration.md` before
      `starter.md`, matching quick-start's outbound link

## 7. Landing-page payoff

- [ ] 7.1 Add the "See it work" block to `index.md` above the fold: the three
      commands plus the real generated `--help` output, rendered with termynal; the
      output text is a state-2 executed snippet so it cannot go stale
- [ ] 7.2 Surface `pip install spoc` directly on the page (currently behind a link)

## 8. Close-out

- [ ] 8.1 Full gate green (`.canon/checks.md`), including the docs snippet suite,
      strict docs build, and both completeness tests
- [ ] 8.2 Docs that describe the docs: update `CONTRIBUTING.md` (or the relevant
      canon check note) with the snippet policy — three states, none silent — and
      the one-command output-regeneration step
- [ ] 8.3 Update `CHANGELOG.md` (docs section) and any architecture diagram touched
      by the new test flow if one exists; Rule 3 commit split by intent
