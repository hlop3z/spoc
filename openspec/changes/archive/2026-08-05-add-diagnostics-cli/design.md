## Context

The kernel's 17 typed exceptions already carry the precision (`failing
segment + valid candidates`) the diagnostics need; nothing surfaces them
before runtime. The scaffold emits a fixed convention — a top-level
`framework.py` exposing `framework` — which gives the CLI a default locate
path (`framework:framework`, the `module:attr` shape uvicorn made familiar).
The console script currently points at `spoc.scaffold.cli:main`, whose parser
owns only `init`. Item 1 shipped `spoc.testing` with exactly the isolation
primitives a dry-run boot needs (`import_state`, `isolated`).

## Goals / Non-Goals

**Goals:**
- `spoc check` / `spoc list` / `spoc explain` as thin adapters over a
  contained `spoc.diagnostics` subpackage with library-first operations.
- One composed CLI: `spoc/cli.py` owns the `spoc` program; scaffold and
  diagnostics each register their subcommands.
- Findings reuse kernel error text verbatim — no second phrasing of the same
  failure.

**Non-Goals:**
- No runtime serving, no watch mode, no auto-fix.
- No plugin system for third-party checks (YAGNI until a third party exists).
- No kernel changes: diagnostics composes public API only.

## Decisions

### D1 — Structure: `spoc.diagnostics` contained subpackage + composed CLI
`src/spoc/diagnostics/` holds `core.py` (operations returning dataclasses:
`Finding`, `CheckReport`, `RecordInfo`) and `locate.py` (framework location).
`src/spoc/cli.py` is the composed entry point: builds the `spoc` parser,
mounts `init` (from `spoc.scaffold.cli.register`) and the three diagnostics
subcommands (from `spoc.diagnostics.cli.register`); `[project.scripts]`
repoints to `spoc.cli:main`. Greenfield: `spoc.scaffold.cli.main` is
refactored into the registration shape rather than kept as a shim; the
scaffold tests move to the composed surface.

### D2 — Dry-run isolation: compose `spoc.testing`
`check`/`list`/`explain` boot inside `spoc.testing`'s scopes (`import_state`
for the import phase, `isolated` for boot+teardown) rather than duplicating
the restoration logic. The harness is shipped, public, zero-dependency API,
and a diagnostic run *is* an isolated dry boot — this is reuse of our own
component, not a new dependency. The kernel-containment AST test learns that
`spoc.diagnostics` (a surface, not kernel) is an allowed importer of
`spoc.testing`; the kernel's own boundary is unchanged.

### D3 — check: config phase, then boot phase
Phase 1 (no imports of app code): `load_spoc_toml` + `validate_spoc_config`,
mode-in-cascade, app-list shape — each failure becomes a `Finding` carrying
the kernel exception's message. Phase 2 (dry boot): construct the framework
from the located declaration and `start()` inside an isolation scope; a
`SpocError` becomes a `Finding`. If the sync path refuses a coroutine hook,
that refusal is recorded as its own finding and the boot retries via
`astart` so the rest of the declaration still gets validated. The report
lists every finding gathered, not just the first.

### D4 — Framework location: convention + `--framework mod:attr` override
Default `framework:framework` (what `spoc init` emits). Override
`--framework pkg.mod:attr`. Location failures state both the convention
searched and the override syntax (spec: actionable). Import of the module
happens with the project directory prepended inside the isolation scope.

### D5 — Output: plain lines, deterministic order, exit codes
`list` prints identifiers sorted (registry enumeration is already
deterministic); `explain` prints facets plus the object's
`module:qualname`; `check` prints one line per finding and a summary. Exit
0 clean / 1 findings or errors — matching the existing CLI's convention. No
color, no table dependency (`dependencies = []`).

### Decision: CLI framework — Adopt the standard library (`argparse`)

- **Status**: approved
- **Why**: The existing ADR "CLI framework for shipped surfaces — Adopt the
  standard library (argparse)" covers this surface verbatim; the composed
  parser is the same tool, extended.
- **Considered**: n/a — decided previously; nothing about the diagnostics
  surface changes the calculus.
- **Isolation**: `spoc/cli.py` and the two `register` adapters; operations
  never see argv.

### Decision: Dry-run isolation — Extend our own `spoc.testing`

- **Status**: approved
- **Why**: The isolation a dry boot needs (path/module snapshot, guaranteed
  shutdown) shipped in item 1 as public API; duplicating it in diagnostics
  would be the exact defect Rule 7 names. No external tool is involved.
- **Considered**: duplicating the ~10 lines in `spoc.diagnostics` (rejected:
  two homes for one behavior); promoting the logic into the kernel (rejected:
  the kernel's contract is that it never touches `sys.path`).
- **Isolation**: diagnostics imports `spoc.testing` only in `core.py`; the
  kernel imports neither.

## Risks / Trade-offs

- [`check` imports app code, so module-level side effects run] → same truth
  Django accepts; documented plainly ("check imports your apps"), and the
  isolation scope restores process state after.
- [A `framework.py` convention miss on custom layouts] → the override plus an
  actionable error naming both paths.
- [Composing the CLI moves the console entry point] → entry-point metadata
  only; no import cycles (cli imports scaffold + diagnostics; neither imports
  cli); scaffold tests updated in the same change (Rule 8).
- [`spoc.testing` in a non-test role reads oddly] → the dependency is on its
  isolation primitives, which are documented as general-purpose scopes; if
  this grates later, the scopes can move to a neutral shared surface without
  breaking either consumer (one home today, rename possible tomorrow).

## Migration Plan

Additive subpackage + entry-point repoint in one change; scaffold CLI
refactor and its test updates land together. Rollback: revert the commit
set; no downstream exists (greenfield).

## Open Questions

None.
