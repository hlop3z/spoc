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

### Decision: Declarative configuration validation — Build (minimal) on the standard library

- **Status**: approved
- **Why**: The reinvention here was never *validating the configuration* — it was having
  written a general-purpose recursive schema engine to do it. The `[spoc]` table is four
  closed keys authored by the project owner, not untrusted input, so the fix is to delete the
  engine and check four keys explicitly: less build, not more. `tomllib` (stdlib) already
  covers the part that is genuinely standard-format parsing and stays. Keeping the package at
  zero `Requires-Dist` matters more here than for an application, because **spoc is a library
  other frameworks build on** — every dependency it takes propagates into every downstream
  framework's tree.
- **Considered**: msgspec (0.21.1, April 2026, ships Python 3.10–3.14 wheels including
  freethreaded, and has no dependencies of its own — it would delete the TOML module outright
  and decode straight into a typed struct; rejected because it is a compiled C extension that
  every downstream consumer would inherit as a platform wheel, and because upstream
  maintenance is slow enough that a community fork, `msgspec-x`, exists to route around it);
  jsonschema (the literal standards-first answer under Rule 9, and it would make the schema
  data rather than code — rejected because it pulls attrs, referencing, and the Rust-compiled
  rpds-py, four transitive dependencies to describe a four-key contract).
- **Rule tension, accepted deliberately**: Rule 9 says adopt the recognized schema standard.
  It is aimed at contracts and identifiers exchanged with the outside world, not a four-key
  internal config file, and the current code violates the *adopt-before-build* rule more
  severely than explicit checks ever could. Revisit if the configuration surface stops being
  closed.
- **Isolation**: the configuration adapter module. The kernel core never reads a file.

### Decision: Component metadata validation — Adopt `ty` statically, build the boundary check

- **Status**: approved
- **Why**: This data originates in Python source that the framework author writes, and never
  crosses a trust boundary. `ty` — already run as `uv run ty check` in `.canon/checks.md` — is
  the adopted tool, and it proves the field types at authoring time, where the mistake is. All
  the kernel needs at registration is one identity assertion that the supplied instance
  matches the kind's declared type. Adopting a runtime validator would re-prove statically
  known facts on the kernel's hottest path.
- **Considered**: msgspec structs for metadata and configuration alike (one tool, one mental
  model — rejected because declaring a kind would then require importing msgspec, making the
  dependency part of spoc's *public API* rather than its internals); no runtime check at all
  (smallest possible, but a wrong type would reach the registry and surface later inside an
  unrelated projection, violating the loud-discovery invariant).
- **Isolation**: the registration boundary in the declaration layer — one check, one place.

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

### Decision: Multi-format loading and collection — Build (thin) over adopted parsers

- **Status**: approved
- **Why**: Adopting `anyconfig` would make it a dependency of *every* format including JSON,
  breaking the bare-install requirement `format-codecs` already states — a conflict with an
  approved spec requirement, not a preference. What remains to build is a dispatch table, a
  directory walk, key derivation, and collision refusal — none of which is standard-format
  parsing, and every parser underneath it is adopted.
- **Considered**: adopt `anyconfig` (covers ~90% of the codec layer, but the bare-install
  conflict is fatal and its query layer is jmespath, so RFC 9535 would still be a second
  dependency); adopt `dynaconf` (same conflict, plus it re-owns the environment layering
  `_MODE_CASCADE` already implements, and is a settings framework rather than a codec layer).
- **Isolation**: the `Codec` port. Calling code sees the port, never a codec.

### Decision: XML dict convention — Adopt `xmltodict`

- **Status**: approved
- **Why**: Maintained (1.0.4, February 2026), MIT, pure Python with no dependencies. Its
  `force_list` accepts a **callable** receiving `(path, key, value)` — the precise extension
  point the declared-repeating-*paths* design needs, which the tag-name form alone could not
  express. `unparse` covers the write direction without a second library.
- **Considered**: build over stdlib `ElementTree` (zero dependencies and `Element` is close to
  the right shape, but it is hand-rolling standard-format parsing against the canon, and
  `.text`/`.tail` mixed-content handling is where it would go wrong); adopt `xmljson` for a
  named convention (implements all six named conventions but is unmaintained and its own
  documentation redirects to `xmltodict` — a hard reject on maintenance).
- **Note**: there is no de-jure XML-to-JSON standard, deliberately — W3C standardized the
  opposite direction (`fn:json-to-xml`) because the mapping is lossy on attributes, namespaces,
  ordering, and mixed content. This convention is therefore necessarily a de-facto adoption.
  For CSV the situation is the reverse: `csv2json` (W3C Recommendation, 2015) *is* de jure, and
  its minimal-mode output is what stdlib `csv.DictReader` already produces, so standards
  alignment came free. CSVW's standard mode with a JSON-LD descriptor is the named upgrade path
  if typed columns are ever needed.
- **Isolation**: one codec adapter, which owns the path-matching predicate handed to
  `force_list`.

### Decision: JSON Pointer and JSONPath engine — Adopt `python-jsonpath`

- **Status**: approved
- **Why**: One MIT dependency with no third-party requirements covers both access standards —
  RFC 6901 for exact addressing and RFC 9535 for querying — where the alternative needs two.
  Version 2.2.1 (July 2026) also ships RFC 6902.
- **Considered**: adopt `jsonpath-rfc9535` plus a separate pointer library (strict conformance
  with no superset ambiguity, at the cost of a second dependency); adopt `jsonpath-ng`
  (predates the RFC and implements a pre-standard dialect — rejected on those grounds before
  the gate).
- **Criterion**: passes the JSONPath Compliance Test Suite.
- **Risk accepted**: `python-jsonpath` is a deliberate *superset* of RFC 9535 — its
  strict-conformance sibling exists for that reason. Strictness is reached by pinning the
  RFC-strict entry points via sentinel tokens; if that ever proves unavailable, the fallback is
  the two-dependency option above. The companion `iregexp-check` is what makes the RFC's own
  `match()`/`search()` functions available, so conformance is not partial.
- **Isolation**: an access module that no codec imports.

### Decision: YAML parser — Adopt `ruamel.yaml`

- **Status**: approved
- **Why**: YAML 1.2 is a strict JSON superset, which matches the "IR is a JSON value" contract
  exactly rather than approximating it, and it avoids the Norway problem by specification
  rather than by patching. PyYAML implements YAML **1.1**, whose implicit booleans parse `NO`
  as `False` and whose sexagesimal rule parses `12:30` as `750`. `ruamel.yaml` dropped its
  C-library dependency in 0.19.1. Maturity and enterprise adoption were tested explicitly and
  pass: aws-cli v2, ansible-lint, mitmproxy, conda, esphome, jupyterlab-server,
  check-jsonschema, ~0.5M downloads/day.
- **Considered**: adopt `PyYAML` as-is (better governance — multi-maintainer, on GitHub,
  ubiquitous — but inherits YAML 1.1's implicit-boolean and sexagesimal footguns knowingly);
  extend `PyYAML` by narrowing its bool resolver (~5 lines, keeps PyYAML's governance and kills
  the headline footgun, but leaves SPOC speaking a third dialect that disagrees with every
  other PyYAML-based tool, and the quieter 1.1 quirks remain).
- **Risk accepted**: single maintainer, hosted on SourceForge Mercurial, with a community fork
  (`ruyaml`) existing explicitly "to secure the future of the library, mainly by having a pool
  of maintainers." Bounded two ways: the `Codec` port makes a backend swap a one-adapter
  change, and `ruyaml` is a drop-in replacement if upstream stalls. **Revisit ~August 2027.**
- **Isolation**: one codec adapter, restricted to safe loading.

### Decision: Formats packaging — one distribution, containment enforced by tests

- **Status**: approved. **Supersedes** "Multi-distribution packaging — Adopt uv
  workspaces" (recorded in the archived change
  `openspec/changes/archive/2026-08-04-production-hardening/design.md`, D8), reversed
  before anything was published.
- **Why**: SPOC is the single point of connections and reading data files is a
  capability of that point, not a separate context. The split's unique benefits
  (independent cadence, wheel purity) solve problems this project does not have, while
  its costs are immediate: a second PyPI project, a second import name, a weaker
  one-install story. The defects the split fixed — `FormatError` subclassing
  `SpocError`, a blurred import boundary — are orthogonal to packaging and stay fixed,
  now pinned by the test suite (the kernel never imports `spoc.formats`; importing
  `spoc` never loads it). Extras remain the feature flags, so `dependencies = []`
  still holds for the bare install.
- **Considered**: keeping two distributions (operational cost with no current
  benefit); `spoc` depending on `spoc-formats` with a re-export (reintroduces a
  kernel→formats dependency direction the boundary forbids).
- **Isolation**: `src/spoc/formats/` only; the boundary tests in
  `tests/test_formats.py` are what a future re-split would lean on — the code stays
  split-ready indefinitely.
