## Why

Two scaffold gaps against the Django slice remain. First, a template set can
only be named if it is installed: the scaffold-templates spec already
requires a filesystem-directory reference to resolve, but the source adapter
resolves only the built-in set and entry points — a spec-implementation gap.
Second, adding an app to an existing project is manual copying; the
generator that knows the app shape should generate it (`startapp` parity),
and SPOC can do one better: the project's own declaration already states the
kinds, so the new app's modules are derivable rather than restated.

## What Changes

- A template set reference that designates a filesystem directory resolves
  and generates, identically to an installed set — closing the stated spec
  gap. Unknown references still fail naming the candidates.
- A new `spoc app <name>` command generates one app into an existing
  project: one module per kind, each holding a declared component, exactly
  the shape `init` emits. It refuses to overwrite an existing app and never
  edits the project's configuration — it prints the exact line to add
  (Django-startapp parity; config stays the author's file).
- The new app's kinds are derived from the project's framework declaration
  (located by the diagnostics convention) when not stated; `--kinds`
  overrides. Derivation happens in the CLI composition root — the scaffold
  operation stays pure and takes kinds as data.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `scaffold-templates`: "A template set is replaceable" gains an explicit
  scenario — a directory path is a resolvable template set reference.
- `project-scaffolding`: gains an "Adding an app to an existing project"
  requirement (generation shape, refusal on existing app, configuration
  never edited, kinds derived from the declaration).

## Impact

- Changed code: `spoc.scaffold.sources` (directory resolution),
  `spoc.scaffold.operations` (an `add_app` operation), `spoc.scaffold.cli` /
  `spoc.cli` (the `app` subcommand; kinds derivation wired in the
  composition root via `spoc.diagnostics.locate`).
- Dependencies: none — no TOML editing happens (the prior "TOML writing —
  dissolved by scope" ADR stays dissolved because configuration is printed,
  not edited).
- Docs: CLI page gains `spoc app`; the init help's "add apps by copying"
  wording updates.
