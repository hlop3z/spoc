## Context

The scaffold's ports already carry most of this: `load_from_directory`
exists but `InstalledTemplateSources.load` never calls it for a path;
`build_plan` renders any file subset; the manifest marks app-shaped files by
their `$app_name` targets. `spoc init app <name>` cannot be the CLI shape —
`init`'s positional is the project name, so `app` would scaffold a project
called "app". The prior ADRs bind this change: template rendering stays
`string.Template` (Build-thin), TOML editing stays dissolved (config is
printed, not edited), argparse stays the CLI. Kinds live in `framework.py`
code, so deriving them requires an import — which `spoc.diagnostics.locate`
already does safely inside an isolation scope.

## Goals / Non-Goals

**Goals:**
- `--template <path>` resolves a directory containing `manifest.toml`.
- `spoc app <name>`: generate one app into an existing project, kinds
  derived from the located declaration, `--kinds` override, config printed.
- The scaffold operation layer stays pure (kinds arrive as data); all
  cross-subpackage wiring stays in the composition root (`spoc.cli`).

**Non-Goals:**
- No URL/archive template fetching (network + extraction is a different
  trust surface; a downloaded directory already works via the path form —
  revisit on demand).
- No config editing (the dissolved TOML ADR stays dissolved).
- No new template set: the app files of the selected set are reused.

## Decisions

### D1 — Directory resolution inside the existing source adapter
`InstalledTemplateSources.load(ref)`: when `ref` contains a path separator
or names an existing directory, resolve via `load_from_directory`; otherwise
the installed-name path as today. Unknown names still fail listing
candidates; a path without a valid manifest fails naming what was missing
(the loader already does). No new port — the reference grammar widens.

### D2 — `add_app` operation beside `init_project`
`add_app(source, sink, app_name, kinds, template_set)` in
`operations.py`: loads the set, filters its files to those whose target
contains the `$app_name` placeholder (the manifest already distinguishes
them), renders with the same values dict, refuses when the app package
exists, commits through the same sink, and returns the plan plus the exact
`[spoc.apps]` line to print. Pure orchestration, same ports.

### D3 — CLI shape: `spoc app <name>`, composition in `spoc.cli`
A sibling subcommand (`init` can't take it — positional collision). The
handler resolves kinds: `--kinds` if stated, else
`spoc.diagnostics.locate.locate_framework` inside `spoc.testing`'s
`import_state` (the composition root already imports both surfaces; the
scaffold subpackage imports neither). Misses fail naming both paths, per
spec.

### D4 — App destination: `apps/<name>` under the project root
The built-in manifest emits apps under `apps/`; `spoc app` targets the same
convention, with `--path` for the project root (default cwd) — mirroring
`init`'s flag.

### Decision: App installation entry — print the exact line, never edit config

- **Status**: approved
- **Why**: Auto-editing `spoc.toml` needs comment-preserving round-trip TOML
  (tomlkit) — as a runtime dependency it breaks `dependencies = []`; behind
  an extra it forks behavior on installation state. Printing the exact
  `[spoc.apps]` entry is Django-startapp parity, keeps config the author's
  file, and keeps the "TOML writing — dissolved by scope" ADR dissolved.
- **Considered**: tomlkit behind a new extra (automation sometimes absent,
  two behavior modes); tomli-w via the existing extra (destroys the config
  file's comments — rejected by the prior ADR for exactly this).
- **Isolation**: n/a — no editing code exists anywhere.

## Risks / Trade-offs

- [A custom template set may have no `$app_name`-marked files] → then the
  set does not support app addition; refuse naming the set and what was
  looked for.
- [Deriving kinds imports project code] → same documented truth as `spoc
  check`; the isolation scope restores state, and `--kinds` avoids the
  import entirely.
- [`apps/` convention may not match a custom layout] → `--path` targets the
  root; the app lands where the template set's own targets say, so a custom
  set controls its own layout.

## Migration Plan

Additive: a wider reference grammar, one new operation, one new subcommand.
Rollback: revert. No downstream (greenfield).

## Open Questions

None.
