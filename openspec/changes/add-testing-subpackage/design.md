## Context

The suite already contains the machinery downstream users need — `make_project`
and the autouse `clean_sys_path_and_modules` fixture in `tests/test_framework.py`
(variants repeated across other test modules) — but it is private, duplicated,
and unshippable. Django's equivalent slice ships `override_settings` /
`isolate_apps`; SPOC ships nothing. The kernel itself needs no change: mode is
read from `config/spoc.toml` at `start()`, boot state is instance-scoped, and
teardown is `shutdown()` plus restoring `sys.path` / `sys.modules`.

Constraints: `dependencies = []` is an invariant; one distribution forever
(extras are the feature flags, no new PyPI package); contained subpackages
(`formats`, `scaffold`) set the precedent — the kernel never imports them, and
the boundary is pinned by tests.

## Goals / Non-Goals

**Goals:**
- Ship the harness as `spoc.testing`, a third contained subpackage.
- Surface it as pytest fixtures via the `pytest11` entry point in the same
  distribution, inert when pytest is absent.
- Migrate the suite onto the harness so the harness is proven by the project's
  own 425 tests, and the duplication is deleted (Rule 7).

**Non-Goals:**
- No kernel API changes (no `mode=` parameter on `start()`, no settings object).
- No unittest/nose adapters — pytest only; the plain context-manager API is the
  runner-agnostic fallback.
- No test-time reimplementation of boot: the harness composes public
  `Framework` APIs, never reaches into private state.

## Decisions

### D1 — Structure: `spoc.testing` as a contained subpackage
Mirror `spoc.formats`: `src/spoc/testing/` with a small `core.py` (isolation
scope), `tree.py` (app-tree builder), and `plugin.py` (pytest fixtures).
`spoc/__init__.py` does not import it; a boundary test pins that importing
`spoc` and booting a framework never loads `spoc.testing`. Dependency
direction: `testing` → kernel public API only.

### D2 — Isolation scope: context manager over public API
`isolated(base_dir, *kinds | framework=...)` snapshots `sys.path` and
`sys.modules` keys, yields a started (or ready-to-start) `Framework`, and on
exit calls `shutdown()` if started and restores the snapshots. This is the
existing autouse fixture's logic, promoted verbatim — not rewritten.
Alternative considered: an `unittest.TestCase` base class — rejected, the
context manager composes with any runner and the pytest plugin wraps it.

### D3 — App-tree builder: declarative dataclass over the proven helper
`ProjectTree(apps={...}, config={...})` with `.build(tmp_path) -> Path` is
`make_project` generalized: N apps, arbitrary module bodies, config table
entries merged into `spoc.toml`. TOML content is emitted by `tomli-w` behind
the existing `toml` extra (see the Decisions ADRs — the scaffold has no
emitter; it substitutes `.tmpl` files, which cannot express arbitrary config
dicts). Module bodies are
caller-supplied source strings dedented on write; the builder owns layout
conventions (`config/spoc.toml`, package `__init__.py`), not content.

### D4 — Mode override: config-file swap, not kernel patching
Mode is read from `spoc.toml` at boot, so `mode(tree_path, "staging")` rewrites
the file's `spoc.mode` value on enter and restores the original bytes on exit
(finally). The caller boots inside the scope. Alternatives rejected:
monkeypatching `load_spoc_toml` (couples harness to kernel internals) and a
`start(mode=...)` kernel parameter (kernel change out of scope; revisit only if
file-swap proves insufficient).

### D5 — Pytest plugin: `pytest11` entry point in the one distribution
`[project.entry-points.pytest11] spoc = "spoc.testing.plugin"` — the standard
discovery mechanism (adopt; see /ai:decide ADR). The entry point is metadata:
pytest imports `plugin.py` only when pytest itself runs, so the runtime
environment never loads it and pytest stays a dev-group dependency. `plugin.py`
imports pytest at module top — safe because only pytest imports the module.
Fixtures: `spoc_tree` (builder factory bound to `tmp_path`), `spoc_isolated`
(factory returning the D2 context manager), each a thin adapter over the core —
no logic of its own.

### D6 — Suite migration in the same change
`tests/` swap hand-rolled helpers for `spoc.testing` where equivalent
(coherence over minimal diff, Rule 7). Tests that deliberately exercise raw
layouts (config edge cases, malformed trees) keep their explicit setup.

### Decision: TOML generation and mutation in the harness — Adopt `tomli-w`

- **Status**: approved
- **Why**: Standard-format serialization is never hand-rolled; `tomli-w` already ships as the
  `toml` extra and in the dev group, so this adds zero new dependencies. Read → mutate → dump
  loses comments only *inside* the override scope, and the scope restores the original bytes
  on exit, so the loss is unobservable. Lazy import with a loud error naming the extra — the
  exact `formats` codec pattern.
- **Considered**: tomlkit (comment-preserving round-trip, the old ADR's answer — but its only
  advantage is invisible here and it would be a new dependency); template re-emission via
  `string.Template` (zero deps, but restricts the mode override to builder-created trees).
- **Isolation**: one emission adapter in `spoc.testing.tree`; the kernel's `tomllib` read path
  untouched. Supersedes the revisit clause of "TOML writing — not needed, dissolved by scope".

### Decision: Isolation harness — Build (thin) on the kernel's public API

- **Status**: approved
- **Why**: No OSS knows SPOC's boot lifecycle; a framework's test harness is inherently its
  own (django.test precedent). The logic is promoted verbatim from the suite's proven autouse
  fixture, not written fresh, and composes only public `Framework` APIs.
- **Considered**: pytest primitives only (monkeypatch/pytester — couples the harness to one
  runner and still cannot shut a `Framework` down).
- **Isolation**: `spoc.testing.core`; runner adapters (the pytest plugin) sit above it.

### Decision: Fixture surfacing — Adopt pytest's `pytest11` entry point

- **Status**: approved
- **Why**: The standard discovery mechanism every pytest plugin uses; metadata-only at
  runtime, so pytest never becomes a runtime dependency and the one-distribution mandate
  holds.
- **Considered**: documented `pytest_plugins` conftest import (no auto-discovery, worse DX);
  a separate plugin distribution (violates the one-distribution mandate).
- **Isolation**: `spoc.testing.plugin`, imported only by pytest itself.

## Risks / Trade-offs

- [Harness bugs mask kernel bugs once the suite depends on it] → the harness
  gets its own black-box tests first (spec scenarios), and boundary/behavior
  tests never assert through the harness alone.
- [File-swap mode override races under parallel test runners sharing a tree] →
  documented: each test builds its own tree via the builder; trees are per-test
  `tmp_path`, so nothing is shared.
- [Entry point loads for every downstream pytest run, even non-SPOC projects] →
  plugin module stays tiny and import-cheap; fixtures are lazy; this is the
  standard cost every pytest plugin accepts.
- [`sys.modules` snapshot/restore can strand C-extension state] → harness only
  deletes modules added during the scope (the proven fixture's exact behavior),
  never reloads preexisting ones.

## Migration Plan

Additive: new subpackage + entry point, then suite migration commit by commit.
Rollback is deleting the subpackage and the entry-point table; no downstream
exists yet (greenfield).

## Open Questions

None — resolved during design; D4 notes the one revisit trigger.
