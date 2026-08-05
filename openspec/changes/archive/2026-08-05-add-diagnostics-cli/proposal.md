## Why

A misdeclared project today fails at runtime, when `start()` raises — the
kernel's typed errors are precise, but nothing surfaces them *before* boot,
and nothing lets a developer inspect the registry without writing a script.
Django's slice ships both (`manage.py check`, `manage.py inspectdb`-style
introspection); SPOC's registry-first design makes them cheap: the registry
is the whole world, so checking and explaining are enumeration.

## What Changes

- `spoc check [path]` — validate a project before it ships: configuration
  problems (malformed/typo'd mode, invalid app lists, cascade errors),
  unresolvable app or plugin references, dependency cycles, identity
  collisions, and coroutine hooks that a sync start would refuse. Reports
  every finding with the kernel's existing precision (failing segment, valid
  candidates), exit code reflects the outcome.
- `spoc list [path]` — enumerate the registry of a booted-then-shut-down
  project: every canonical identifier, optionally filtered by kind or
  namespace facet.
- `spoc explain <identifier> [path]` — resolve one identifier and print the
  record's facets and the object behind it; a typo fails with the kernel's
  candidate-naming error, never silently.
- The commands locate the project's framework declaration by the scaffold's
  own convention (a module exposing the framework object), overridable for
  projects shaped differently.
- The console script becomes a composed surface: the existing `init`
  subcommand is unchanged; check/list/explain mount beside it. All new logic
  lives in a contained `spoc.diagnostics` subpackage; every CLI entry stays a
  thin adapter.

## Capabilities

### New Capabilities

- `project-diagnostics`: pre-runtime validation of a project's declaration
  and configuration, and read-only registry introspection (enumerate,
  resolve-and-describe), invocable identically from the CLI or as library
  calls.

### Modified Capabilities

<!-- none — scaffolding behavior is untouched; the console script gains
     subcommands, which project-scaffolding's spec does not constrain -->

## Impact

- New code: `src/spoc/diagnostics/` (contained subpackage), `src/spoc/cli.py`
  (thin composed entry point), `[project.scripts]` repointed to it.
- Changed code: `spoc.scaffold.cli` exposes its `init` wiring for composition;
  behavior identical.
- Dependencies: none — kernel public API and standard library only;
  `dependencies = []` invariant intact.
- Docs: CLI page for the three commands; architecture diagram gains the
  fourth contained subpackage.
