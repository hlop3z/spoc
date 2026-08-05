# Production Hardening

## Why

A harsh production-readiness review scored the kernel's craft high but found the
gap between "clean library" and "infrastructure a business can sit on": the boot
mutates process-global import state (`sys.path[0]`) and the filesystem, the
lifecycle cannot await anything, no concurrency contract exists, restart makes a
"clean boot" claim the module cache cannot honor, the registry silently returns a
different identity than the caller asked for, the mode set is hardcoded to one
company-shaped taxonomy, the Python floor (3.13) excludes most of the installed
base, and the kernel distribution ships an unrelated data-formats toolkit.
Nobody depends on SPOC yet (greenfield), so every one of these is fixable now
without compatibility machinery — and only now.

## What Changes

- **BREAKING** Apps are addressed by dotted module path and imported through the
  normal import system. The kernel never mutates `sys.path`, never creates
  directories, and never shadows the standard library. Boot acquires no
  process-global state beyond Python's own module cache.
- Lifecycle goes async-capable: an async start/shutdown path on the framework,
  and kind hooks plus module `initialize`/`teardown` may be coroutines. The sync
  path remains and refuses async hooks loudly rather than half-running them.
- A concurrency contract is defined, documented, and tested: registration is
  serialized and safe under concurrent writers; reads after a completed start
  are safe without coordination; start/shutdown are serialized against each
  other and against themselves.
- Restart semantics become honest: shutdown's contract states exactly what is
  reset (registry, loader, config) and what persists (Python's module cache and
  any module-level state), instead of claiming a "clean boot".
- **BREAKING** Re-registering an already-registered object under a different
  identity raises instead of silently returning the prior record. Idempotent
  re-registration under the *same* identity remains a no-op.
- The mode set opens: projects may declare their own modes and cascade order in
  configuration; the current development → staging → production cascade becomes
  the default, not the law.
- The Python floor drops from 3.13 to 3.12.
- **BREAKING** `spoc.formats` leaves the `spoc` distribution and becomes its own
  distribution with its own import name; the kernel's zero-dependency invariant
  and the sidecar's extras move with it.

## Capabilities

### New Capabilities

None — every change lands in an existing capability.

### Modified Capabilities

- `framework-lifecycle`: boot must be free of process-global side effects
  (no import-path mutation, no filesystem writes); an async start/shutdown path
  exists and hooks may be coroutines; start/shutdown are mutually serialized;
  shutdown's reset contract states what persists.
- `component-registry`: registering an already-registered object under a
  different identity is an error; concurrent registration is serialized and
  loses no records.
- `framework-declaration`: kind lifecycle hooks may be declared as coroutine
  functions; the declaration records this so the lifecycle can dispatch them.
- `project-configuration`: apps are declared as dotted module paths; the mode
  set and its cascade are declarable in configuration with the current triple
  as default.
The formats split (`data-access`, `data-collection`, `format-codecs`) changes
no requirement — behavior is identical, only the distribution and import name
move. It is recorded in design and tasks, not as delta specs.

## Impact

- **Code**: `spoc/core/paths.py` is deleted; `spoc/core/loader.py`,
  `spoc/framework.py`, `spoc/core/registry.py`, `spoc/core/config.py` change;
  `src/spoc/formats/` moves out of the `spoc` package tree.
- **Packaging**: the repo becomes a two-distribution workspace (kernel +
  formats); extras (`yaml`, `xml`, `toml`, `query`, `full`) move to the formats
  distribution; `requires-python` drops to `>=3.12` in both.
- **Scaffold**: generated projects must declare apps by dotted path and gain an
  importable apps package; templates change accordingly.
- **Docs & examples**: quick start, architecture diagram, and the examples tree
  update to the dotted-path model and the new formats import name.
- **Tests**: new suites for the concurrency contract and async lifecycle;
  `tests/test_formats.py` moves to the formats distribution.
- **Build-vs-adopt decisions deferred to /ai:decide**: the async execution
  approach, the workspace/packaging mechanism, and the concurrency primitive.
