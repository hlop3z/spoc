## Why

Every downstream user of SPOC must hand-roll the same test machinery our own suite
hand-rolls today (`make_project`, the `sys.path`/`sys.modules` cleanup fixture in
`tests/test_framework.py`): build an app tree on disk, make it importable, boot a
framework against it, and tear everything down without leaking state between tests.
Django's app-registry slice earns much of its score from exactly this machinery
(`override_settings`, `isolate_apps`); SPOC has nothing shippable, which is the
single largest capability gap on that slice.

## What Changes

- New contained subpackage `spoc.testing` — same containment contract as
  `spoc.formats` and `spoc.scaffold`: the kernel never imports it, importing
  `spoc` never loads it, zero runtime dependencies preserved.
- An isolated-framework harness: construct a fresh `Framework` against a
  project tree with guaranteed teardown (shutdown + `sys.path`/`sys.modules`
  restoration), usable as a context manager without any test runner.
- An app-tree builder: declare apps, modules, and `spoc.toml` content
  programmatically and get a bootable project directory — promoted from the
  `make_project` helper the suite already proves out, not written fresh.
- A mode-override context manager: run a block under a different mode cascade
  and restore the prior configuration on exit.
- An in-distribution pytest plugin exposing the above as fixtures via the
  `pytest11` entry point — one distribution, no new package; pytest is never a
  runtime dependency (the plugin degrades to no-op when pytest is absent).
- The existing test suite migrates to consume `spoc.testing` where it currently
  hand-rolls the same machinery (the harness is then proven by the suite itself).

## Capabilities

### New Capabilities

- `test-harness`: isolated framework construction and teardown, app-tree
  building, and mode override for tests — importable without any test runner.
- `pytest-integration`: the harness surfaced as pytest fixtures through an
  entry point shipped in the one `spoc` distribution, inert unless pytest
  loads it.

### Modified Capabilities

<!-- none — the kernel's observable behavior does not change; the harness is a
     new consumer of existing contracts -->

## Impact

- New code: `src/spoc/testing/` (contained subpackage), `[project.entry-points.pytest11]`
  in `pyproject.toml`.
- Changed code: `tests/` migrate from hand-rolled helpers to the subpackage;
  boundary tests pin that the kernel does not import `spoc.testing`.
- Dependencies: none at runtime (`dependencies = []` invariant intact); pytest
  remains a dev-group dependency only.
- Docs: new how-to page ("testing your app") in the mkdocs site; README feature
  bullet.
