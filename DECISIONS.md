# Decisions

Build-vs-adopt decisions recorded per `/ai:decide`. This is the fallback home the command
uses when a project has no active OpenSpec change and no `PROJECT.md`.

Concrete tool names live here only — `.canon/` and `openspec/specs/` stay abstract.

## Decisions

### Decision: Counting lines of code — Adopt tokei

- **Status**: approved
- **Why**: Mature, fast, covers every language, and packaged on every platform we target
  (`winget install XAMPPRocky.Tokei`, `brew install tokei`, `scoop install tokei`,
  `cargo install tokei`). There was never a reason to write one.
- **Supersedes**: a hand-written Go `loc` tool built earlier in this repo. That was a
  straight violation of the adopt-before-build rule — it shipped a bug tokei never had
  (counting compiled binaries as source) and covered less. It has been deleted; git history
  keeps it (Rule 5).
- **Considered**: scc (also excellent and actively maintained, adds cyclomatic complexity and
  COCOMO estimates — the better pick if those metrics are ever wanted); cloc (Perl, slower,
  the original).
- **Isolation**: invoked as a command from `.canon/checks.md`. Nothing imports it, so
  swapping to scc means editing one row.

### Decision: Obtaining adopted CLIs — Build a thin `ensure` command

- **Status**: approved
- **Why**: Adopting a tool only works if it is actually installed, and "it isn't installed"
  must never become the excuse to rebuild it. `ensure` is glue over installers that already
  exist: it checks PATH, then the OS package manager, then cargo, and only installs a Rust
  toolchain behind an explicit `--allow-rustup` because pulling in a compiler to obtain one
  binary is the heaviest possible answer.
- **Considered**: mise and asdf (mature tool-version managers, but bootstrapping one to
  obtain a single tool is heavier than using the package manager already on the machine);
  eget and ubi (fetch release binaries from GitHub — rejected because **tokei publishes no
  release assets at all**, verified against the GitHub API, so there is nothing to fetch);
  documenting the install commands in a README and installing by hand (no detection, breaks
  the check run for anyone who skipped it).
- **Scope limit**: if a third tool ever needs release-binary downloading, adopt eget or ubi
  rather than growing this. That is the line where glue would become a reimplementation.
- **Isolation**: `scripts/go/internal/ensure`, invoked by `cmd/ensure`. No other tool imports it.

### Decision: Python dependency and workspace management — Adopt uv

- **Status**: approved
- **Why**: Specified by the user, and it is the only Python tool that covers workspaces, the
  lockfile, the interpreter, and PEP 723 single-file scripts in one binary — which is exactly
  the reusable/disposable split this workshop needs.
- **Considered**: Poetry (no PEP 723 script support, slower); pip + venv (no workspace or
  lockfile story).
- **Isolation**: `scripts/py/pyproject.toml`. Tool source imports nothing from uv; swapping it
  would change the run commands, not any tool's code.

### Decision: Go CLI framework — Adopt cobra

- **Status**: approved
- **Why**: The mature standard (kubectl, gh, hugo; ~44k stars) with subcommands, generated
  help, and shell completions. The reference tool's own shape — download / retry / merge /
  validate / cleanup — is a subcommand tree, which is where stdlib `flag` fails outright.
  Boilerplate cost is paid by the scaffold, not by hand.
- **Considered**: urfave/cli (lighter, mature, weaker completions); stdlib `flag` (zero deps,
  but no short/long pairing, no required args, no subcommands — hand-rolling those is exactly
  what the never-hand-roll rule forbids).
- **Isolation**: `cmd/<name>/main.go` only. Logic lives in `internal/`, which imports no CLI
  library, so replacing cobra touches adapters alone.

### Decision: Python CLI framework — Adopt cyclopts

- **Status**: approved
- **Scope**: workshop tools under `scripts/`, which ship to nobody. It does **not** govern CLI
  surfaces inside the published `spoc` package, where a dependency would break the stated
  `dependencies = []` invariant — see "CLI framework for shipped surfaces" below.
- **Why**: Beats typer on the two highest-weighted rubric criteria. Feature coverage (30%):
  Unions, Literals, and mutually exclusive groups, none of which typer supports. Documentation
  (10%): ships API docs; typer does not. Maintenance is strong — 138 releases, latest days
  old, 56 contributors, Apache-2.0. Its type-hint-driven design also makes promotion cheap:
  a lab function becomes a CLI without being rewritten.
- **Considered**: typer (larger community, ~17k stars vs ~1.2k — the one criterion cyclopts
  loses, weighted 10%; no Union support); click (mature and explicit, but more boilerplate and
  no type-hint inference); argparse (stdlib, zero deps, verbose and fully manual validation).
- **Risk accepted**: smaller community means a thinner bus factor than typer's. Mitigated by
  the isolation below — a migration would be confined to `cli.py` files.
- **Isolation**: `src/<name>/cli.py` only. `core.py` holds plain functions that import no CLI
  library.

### Decision: Disposable script packaging — Adopt PEP 723 inline metadata

- **Status**: approved
- **Why**: A uv workspace member needs a `pyproject.toml` and enters the shared lockfile,
  which is the opposite of disposable — every experiment would become a resolution event and
  every deletion would leave the lockfile inconsistent. PEP 723 keeps dependencies in the file
  that uses them and runs in an ephemeral environment. Verified working with `uv run`.
- **Considered**: workspace member per experiment (lockfile churn, deletion inconsistency);
  gitignored member directory (breaks `uv sync` on a fresh clone, since the lockfile
  references a path that isn't there); a shared `lab` package with pooled dependencies (one
  experiment's dependency becomes everyone's).
- **Isolation**: `scripts/py/lab/`, listed under `exclude` in the workspace root.

### Decision: Project generation and template rendering — Build (thin) on the standard library

- **Status**: approved
- **Why**: `string.Template` matches the scaffolder's spec by construction where Jinja would
  have to be constrained into it — the contract requires substitution values to be a declared,
  enumerable set that is never evaluated, and `Template.get_identifiers()` satisfies the
  enumerability requirement in one call. Adopting a generator would also add a separate install
  step to the one command whose whole purpose is removing friction.
- **Considered**: copier (strong at new-project generation and its `update` feature is real,
  but carries Jinja and needs its own install for a once-per-project command); cookiecutter
  (the incumbent, but renders a template directory to a *different* output directory by design
  — it cannot render in place, which ruled it out while the change still had an `add app`
  operation).
- **Precedent**: Django's `TemplateCommand` backs `startproject` with no external templating
  dependency. This is that shape.
- **Isolation**: the `TemplateSource` port. The renderer is called from one adapter; swapping
  to Jinja later changes that adapter and nothing in the core.

### Decision: CLI framework for shipped surfaces — Adopt the standard library (`argparse`)

- **Status**: approved
- **Why**: Zero dependencies, so a CLI can ship inside the published package with
  `dependencies = []` untouched — verified in the built wheel, which declares no
  `Requires-Dist`. One command with a handful of flags is squarely inside what argparse does
  well.
- **Considered**: cyclopts (this project's choice for *workshop* tools, where nothing ships —
  that ADR does not transfer, because dependency weight counts against a stated invariant
  here); typer (same objection, heavier tree).
- **Note**: the Go ADR above rejects stdlib `flag` for lacking subcommands. That reasoning is
  Go-specific — Python's `argparse` has subparsers, required arguments, and short/long pairing.
- **Isolation**: the CLI entry-point module only. The operation is callable without argv.

### Decision: Filesystem write safety — Build (thin) on standard-library primitives

- **Status**: approved
- **Why**: The requirement is narrow — stage, verify, commit, never traverse outside the target
  — and `tempfile`, `os.replace` (atomic within a filesystem), and
  `Path.resolve().is_relative_to()` are the adopted, well-tested primitives underneath it. A
  library here would be more surface than the problem.
- **Considered**: delegating staging to an adopted generator (collapsed into the decision
  above and was rejected with it); a filesystem-transaction library (none mature enough to
  outweigh ~40 lines of stdlib).
- **Isolation**: the `ProjectSink` port.

### Decision: TOML writing — not needed, dissolved by scope

- **Status**: approved
- **Why**: Stdlib `tomllib` is read-only, and comment-preserving edits require `tomlkit` — but
  only when *editing* an existing file. Dropping the scaffolder's `add app` operation left only
  emission of a fresh `spoc.toml` from a template, which is plain text substitution. The
  concern was removed rather than solved, which is why the scaffolder still ships with no
  dependencies.
- **Considered**: adopt tomlkit (the correct answer had `add app` survived — round-trip TOML
  editing is standard-format serialization and therefore never hand-rolled); hand-rolled TOML
  editing (rejected outright on that same rule).
- **Isolation**: n/a — the kernel's existing `tomllib` read path is untouched.
