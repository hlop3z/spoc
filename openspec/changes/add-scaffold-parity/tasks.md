## 1. Directory template sets

- [x] 1.1 Widen `InstalledTemplateSources.load` to resolve directory references via the existing `load_from_directory`; unknown names still list candidates
- [x] 1.2 Tests: directory-path set generates identically; path without a manifest fails naming it, nothing written

## 2. add_app operation

- [x] 2.1 Implement `add_app` in `operations.py` — filter the set's `$app_name`-marked files, render, refuse existing app, return plan + the exact `[spoc.apps]` line; refuse a set with no app-marked files
- [x] 2.2 Tests for every `project-scaffolding` delta scenario (shape parity with init, no overwrite, config byte-identical + stated line, derived kinds, actionable double-miss)

## 3. CLI

- [x] 3.1 `spoc app <name>` subcommand: `--kinds` override, else kinds derived via `diagnostics.locate` inside `import_state` (wired in `spoc.cli` only); `--path` and `--template` mirroring `init`
- [x] 3.2 CLI adapter tests (exit codes, printed config line, double-miss message); update `init`'s "add apps by copying" help wording
- [x] 3.3 Full validation per `.canon/checks.md`

## 4. Docs

- [x] 4.1 CLI page: `spoc app` section; README wording if it mentions app addition
