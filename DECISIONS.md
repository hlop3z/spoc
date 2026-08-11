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

- **Status**: superseded by "Origin record serialization — Adopt the standard library (`json`)"
- **Superseded because**: the premise below — that the scaffolder only emits fresh TOML by plain
  text substitution — stopped holding when the origin record was added. The record interpolates
  arbitrary caller-supplied strings into TOML, which is serialization, not substitution, and it
  was already producing unparseable output for any reference containing a backslash or a quote.
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
  `tests/test_formats.py` are the containment contract.
- **Standing constraint (owner mandate, 2026-08-05)**: SPOC ships as **exactly one
  PyPI distribution** — do not split `spoc.formats`, or any future surface, into a
  separate package. A capability that wants optional dependencies gets the same
  treatment formats got: a contained subpackage behind extras, its boundary pinned
  by tests. Re-splitting is not an open option to revisit; it would take a new
  owner decision superseding this one.

### Decision: Archive member admission — Adopt the standard library filter, Extend with our own containment

- **Status**: approved
- **Why**: Standard-format parsing is on the never-hand-roll list, and `tarfile`'s PEP 706
  `filter="data"` is the maintained answer — PEP 721 has pip extracting sdists with it. But it
  cannot be the *sole* control: CVE-2025-4517 (CVSS 9.4) is arbitrary filesystem write via path
  traversal in `filter="data"` itself, patched only in 3.12.11 / 3.13.4, while this project
  requires `>=3.12` and cannot control a user's patch level. Re-verifying each materialized path
  with `resolve().is_relative_to()` makes that CVE — and any future filter bypass — inert, at a
  cost of about six lines against a predicate the sink already uses.
- **Considered**: the filter alone with the floor raised to a patched interpreter (excludes
  3.12.0–3.12.10 users, and makes the next filter CVE ours with no fallback); hand-written
  admission with no filter (hard reject — this is precisely what produced Django's
  CVE-2021-3281 and CVE-2025-59682 in the same feature).
- **Isolation**: the admission step of the remote resolver, behind the `Fetcher` port.

### Decision: Expanded-size and member-count bounds — Build (thin), no dependency

- **Status**: approved
- **Why**: No standard-library API bounds *expanded* size — PEP 706 explicitly does not cover
  it — and the only OSS candidate covers zip but not tar, so adopting it would still leave the
  tar path hand-written while breaking the empty-dependency invariant. Descending to Build is
  justified here because no viable option exists under the stated constraint, not because the
  problem is special: it is a streaming counter that halts at a bound.
- **Considered**: `sunzip` (zip-only, narrow community, and pays a dependency for partial
  coverage); shipping without bounds (leaves a documented denial-of-service vector in a feature
  whose premise is retrieving content from strangers).
- **Isolation**: one function in the retrieval adapter, with each bound a named constant beside
  the concept it bounds. Flagged in `design.md` as the likeliest defect site in this change.

### Decision: Retrieval transport and redirect policy — Adopt the standard library, Extend the redirect handler

- **Status**: approved
- **Why**: Transport is never hand-rolled, and the empty-dependency invariant rules out `httpx`
  and `requests` for a shipped surface. `urllib.request` is the adopted transport; refusing a
  scheme-downgrade redirect is a handler subclass of about a dozen lines. The policy would be
  roughly that size under any client, so a dependency buys ergonomics rather than safety.
- **Considered**: `httpx` behind an extra (reintroduces the two-step install this change exists
  to remove); following redirects with default policy (makes any scheme guarantee decorative,
  since any reference can be redirected onto a weaker location).
- **Isolation**: the `Fetcher` port. Tests run against an in-memory fake and never open a socket.

### Decision: Template reference grammar — Adopt the pip / PEP 508 direct-reference shape

- **Status**: approved
- **Why**: Rule 9 — a reference grammar is an identifier scheme, and inventing one where a
  recognized one applies is a defect. PEP 508 direct references are already fluent to a Python
  audience, and it is the only candidate expressing both an archive reference and a
  revision-pinned VCS reference in one published vocabulary (`@ref` for the pin,
  `#subdirectory=` for the path within). `gh:` is sugar expanding to that shape, not a parallel
  scheme.
- **Considered**: Terraform's `//sub` + `?ref=` (more readable, but foreign to this audience and
  would need its own documentation); giget's `#ref` (closest prior art for this exact feature,
  but no Python-side familiarity).
- **Isolation**: `parse_reference` in the pure core — a total function over strings, tested
  without network or filesystem.

### Decision: Cache location — Build (thin) on the platform conventions

- **Status**: approved
- **Why**: `platformdirs` is the mature answer and there is no standard-library equivalent, but
  taking it as a dependency breaks the invariant, and taking it as an extra reintroduces exactly
  the two-step install this change exists to eliminate. Reading `XDG_CACHE_HOME`,
  `LOCALAPPDATA`, and `~/Library/Caches` directly is about fifteen lines: this adopts the
  platform *conventions*, declining only the library that wraps them.
- **Considered**: `platformdirs` behind a `remote` extra (correct but self-defeating for this
  feature); caching inside the generated project (no platform logic, but no reuse across
  projects, so every new project re-fetches).
- **Isolation**: the `Cache` port. Keyed by exact revision, so retained content is never stale
  for the revision it is held under; swapping to `platformdirs` later changes one adapter.

### Decision: Origin record serialization — Adopt the standard library (`json`)

- **Status**: approved
- **Why**: The record interpolates arbitrary caller-supplied strings — a reference may be
  `C:\templates\mine` or carry a quote — and TOML has no standard-library writer, so emitting it
  as TOML means hand-rolling escaping for a format on the never-hand-roll list. That was not
  hypothetical: the template-substituted TOML record already failed to parse for any
  backslash-bearing reference, and `read_origin` swallows the parse error as "no record", so the
  defect was invisible. `json` in the standard library is a complete serializer for exactly the
  scalar shape this record holds, costs no dependency, and keeps `dependencies = []` intact.
- **Considered**: adopt `tomli-w` 1.2.0 (MIT, zero-dependency, correct — but a base runtime
  dependency for one advisory file overturns the one-distribution/extras-are-feature-flags rule,
  and it cannot write comments either, so the file's explanatory header is lost regardless);
  hand-roll a TOML string escaper (~10 lines, rejected on the never-hand-roll rule — which exists
  for precisely the bug found here).
- **Trade-off accepted**: the record diverges from the repo's TOML idiom, and the comment header
  becomes a `note` field. The divergence tracks a real line — TOML is what a human authors here
  (`spoc.toml`, `manifest.toml`), JSON is what the scaffolder writes and reads for itself.
- **Isolation**: `spoc.scaffold.provenance` — it owns both directions of the record's shape, so
  the writer and `read_origin` cannot drift. Nothing else in the codebase constructs or parses it.

### Decision: Origin record integrity — Build by construction

- **Status**: approved
- **Why**: The record describes a template set to a later operation, so the set must not be able
  to author it. The mechanism is structural rather than defensive: the record's values leave the
  substitution vocabulary entirely, so no rendering path exists through which a set — retrieved
  from anywhere, written by anyone — can reach it. The reserved-destination check is defense in
  depth that makes an attempt *visible*, not the thing that makes it impossible. This is control
  flow inside a scaffolder already decided as Build (thin) on the standard library, and adopting
  anything here would mean adopting a template engine, which the specs forbid outright.
- **Considered**: adopt Copier or cookiecutter wholesale (Copier is the positive precedent —
  it writes `.copier-answers.yml` unconditionally and lets templates only customize it — but
  replacing the scaffolder relitigates an approved decision and adds a runtime dependency to a
  zero-dependency distribution); require every template set to declare the record (fixes
  suppression, not forgery, and taxes every third-party author with a file they did not ask to
  own).
- **Isolation**: `init_project` contributes the record to the plan after `build_plan` has
  rendered the set; the reserved-destination check lives in `validate_template_set` in the pure
  core, beside `_reject_escape`, sourcing the name from `provenance.RECORD_NAME`.

### Decision: Public API surface extraction — Adopt griffe

- **Status**: approved
- **Why**: Determining a Python package's true public API — `__all__` precedence, re-export
  and alias resolution, inherited members, signature changes — is a solved problem, and it is
  the input the stability contract's gate depends on. griffe (ISC, actively maintained, the
  engine under mkdocstrings) does extraction *and* `griffe check` breakage classification
  between two refs, so one adoption serves both the drift check and the release policy's
  compatibility assertions. Its public-API rules already match ours. Verified before building
  on it: it classified a removed export as "Public object was removed" (exit 1) and stayed
  silent on a compatible addition (exit 0). Development-time only — `dependencies = []` holds.
- **Considered**: hand-rolling extraction on `importlib`/`inspect`/`ast` (re-implements
  `__all__` precedence and alias resolution, and yields no breakage classification — the
  `loc`/tokei mistake again); snapshotting the rendered surface into a golden file (cheap and
  does catch drift, but reports only *that* something changed, never what kind, so it cannot
  support the version-increment assertions).
- **Scope limit**: griffe documents that it cannot see console scripts, entry points, or
  extras — roughly half this surface. Those are observed by `apicheck.packaging` from
  `pyproject.toml` and an AST scan, feeding the same core. Adopting the hard part is not the
  same as adopting everything, and the manifest declares kinds no observer covers as
  `unverifiable` rather than passing them silently.
- **Isolation**: `apicheck.extract`, one adapter in `scripts/py/tools/apicheck/`. The diff core
  receives an extracted surface and knows nothing about griffe. Deliberately *not* shipped in
  `src/spoc/`: a checker inside the package would need a tier of its own and would have to
  police itself.

### Decision: Deprecation signal — Extend PEP 702 (`warnings.deprecated` + a 3.12 fallback)

- **Status**: approved
- **Why**: PEP 702 is the standard and satisfies the release policy outright — a
  `DeprecationWarning` consumers can suppress or escalate through normal warning filters, plus
  static visibility for type checkers. It is stdlib from 3.13 (`warnings.deprecated`) while
  this package's floor is 3.12, so ~40 lines bridge the gap. On 3.13+ the stdlib decorator is
  used unchanged, and the fallback deletes itself the day the floor moves to 3.13.
- **Considered**: adopt `typing_extensions`, the canonical backport — rejected outright, it is
  a *runtime* dependency and `dependencies = []` is load-bearing; bump `requires-python` to
  `>=3.13` and drop the fallback entirely (strictly cleaner code, but dropping 3.12 is a scope
  change, not a tooling one — available later at no cost); hand-roll a bespoke decorator
  (reinvents a standard that type checkers already understand).
- **Isolation**: `spoc.core.deprecation` — the single import site. Call sites use the
  decorator and never observe which implementation supplied it. Both paths are tested on every
  interpreter, so the fallback is not left unexercised on versions CI may not run.

### Decision: Reading the withdrawal mark from source — Extend griffe with a stdlib `ast` pass

- **Status**: approved
- **Why**: The gate has to know which elements have entered the deprecation lifecycle without
  executing the package, and no adopted tool supplies that fact. Verified against the installed
  griffe rather than assumed: `Object.deprecated` is initialized to `None` and assigned only by
  the JSON decoder in `_internal/encoders.py` — the static visitor never sets it — and
  `BreakageKind` has twelve members, none of them deprecation-related. So the archived
  `decide-scaffold-surface` note that "griffe already reads `__deprecated__`" is wrong, and
  waiting for upstream is not an option. Griffe stays the adopted extractor for the hard part
  (`__all__` precedence, alias and re-export resolution); recognizing *our own* mark on top of
  it is a project-specific rule with no upstream to adopt. The mark is read with `ast` because
  the message spans implicitly concatenated string literals, which is standard-format parsing —
  on the never-hand-roll list — and because `extract.py` already opens every source file for
  `#:` comment blocks, so it is one more fact from a pass that already happens.
- **Considered**: adopt `memestra` (QuantStack, BSD-3), the one purpose-built static checker for
  deprecated decorators — hard reject on the maturity rubric: Snyk lists it Inactive, pinned at
  0.2.1, ~827 weekly downloads, and it solves the inverse problem, finding call sites in
  consumer code rather than enumerating a package's own marks; wait for ruff, where "warn if
  anything marked deprecated is used" (astral-sh/ruff#14221) is an open request and not a
  shipped feature; extend the existing `_ASSIGN` regex scan — rejected, a regex mishandles the
  two-literal message and hand-rolls parsing of a format the standard library already parses.
- **Isolation**: `apicheck.extract`, the adapter that already owns reaching for source. The core
  receives `Exposure.withdrawal` as a fact and never learns how it was recovered. The mark's own
  sanctioned form remains `spoc.core.deprecation` per the PEP 702 decision above, which is what
  makes "any other spelling is a finding" enforceable rather than aspirational.

### Decision: Reconstructing per-release history — Extend `apicheck.release`

- **Status**: approved
- **Why**: Establishing that a removal completed the lifecycle is a question about three points
  in time — when the mark first appeared, that a full minor release shipped with the element
  still functional, and that it is now gone — and the comparison currently holds two. The
  adapter that answers it already exists: `release.py` materializes a ref's `src/` with
  `git archive` and hands it to the ordinary extractor, precisely so both sides are classified
  by the same rules. What it lacks is version-ordered tag enumeration and a backward walk, both
  of which sit inside that boundary and need no new dependency — ordering comes from
  `packaging.version`, already in use for `declared_version`. The walk is driven by removals and
  stops at the first release lacking the mark, so in the ordinary case it costs nothing.
- **Considered**: adopt griffe's `load_git` — it is publicly exported and does check out a ref,
  but it returns a `Module` where `apicheck` needs a path to run its *own* extractor over (tier
  derivation, `#:` comments, packaging facts), so it would introduce a second way of reading a
  ref, which is the exact failure `release.py`'s docstring exists to prevent; it also creates a
  worktree, taking a repository lock that `git archive` was deliberately chosen to avoid. Build
  a committed per-release surface record, using griffe's JSON dump since it round-trips
  `deprecated` — rejected: it is a cache of what the repository already holds, it adds an
  artifact that can drift from its source, and its only advantage is avoiding a cost the lazy
  walk already reduces to zero.
- **Isolation**: `apicheck.release`, unchanged in role — it reaches for published releases and
  yields facts. The lifecycle verdict itself is pure and lives in `apicheck.core`, which is
  handed an element's per-release presence and marks and knows nothing about git or tags.

### Decision: Incrementing the declared version — Adopt `hatch version`

- **Status**: approved
- **Why**: The version's location is already declared once, in hatchling's own format —
  `[tool.hatch.version] path = "src/spoc/__about__.py"` — because hatchling is the build
  backend. `hatch version <part>` bumps through that same declaration, so adopting it adds
  **no configuration at all** and cannot drift from what the build reads. It supersedes an
  inline-Python regex in `Taskfile.yml` that reimplemented the increment by hand: the
  `loc`/tokei pattern again, and it could only match `\d+\.\d+\.\d+`, so a pre-release or dev
  segment would have crashed it. Verified before adopting: `uvx hatch version minor` took
  0.5.0 → 0.6.0 in ~2s and left the module docstring, `__license__`, and `__author__`
  untouched. Hatch 1.17.1 (July 2026), MIT, maintained by the PyPA.
- **Considered**: `bump-my-version` 1.5.1 (the maintained successor to bump2version and
  bumpversion, both dead upstream — richer, with commit and tag built in, but it pulls nine
  runtime dependencies and needs its own `[tool.bumpversion]` block, a *second* declaration of
  where the version lives beside `[tool.hatch.version]`, and its commit/tag feature duplicates
  `version:release`, which already gates on `task check`); keeping the hand-rolled regex (works
  today, installs nothing, but is the reinvention the adopt-before-build rule forbids).
- **Ruled out before scoring**: `uv version --bump` — verified failing here, *"We cannot get or
  set dynamic project versions in: pyproject.toml"*, since the version is declared `dynamic`.
  `hatch-vcs` / `setuptools-scm`, which derive the version from the tag and would remove the
  chance to mistype it entirely — **hard reject**: `apicheck.release.declared_version` reads
  `__about__.py` statically *before* a tag exists, and `apidiff` gates the surface delta against
  that declared increment. Deriving the version from tags would disable the deprecation
  lifecycle enforcement.
- **Obtaining it**: invoked as `uvx hatch`, so `uv` — already required by `task doctor` — fetches
  it on first use. It needs no entry in `scripts/go/cmd/ensure`, which exists for tools with no
  such self-installing runner (`tokei`).
- **Isolation**: the single internal `version:bump` task in `Taskfile.yml`. The three
  `version:bump:{major,minor,patch}` entry points pass a segment name and know nothing about
  the implementation, so replacing hatch means editing one line.

### Decision: Starter template's surface stack — Adopt the stdlib (no third-party binding)

- **Status**: approved
- **Why**: the kernel is surface-plural ("HTTP, CLI, workers … FastAPI, Robyn, anything"),
  so the starter set generates no transport binding at all: a dependency-free projection
  module (`surface.py`) plus a command surface on stdlib `argparse` — a real, runnable
  application with zero third-party dependencies. Transport bindings are ~15-line
  documented recipes over the projection, each executed by the test suite; the worked
  HTTP recipe uses FastAPI because it is already the `examples` dev-dependency.
- **Considered**: a FastAPI-generating starter (flavors SPOC as an HTTP/FastAPI adjunct
  and demotes every other transport); Litestar (same flavoring plus a new CI dependency);
  per-stack starter sets now (each must generate-and-boot in CI for no present user —
  remains open as later pure-data additions through the `scaffold-templates` contract).
- **Isolation**: template data only (`src/spoc/scaffold/templates/starter/`); binding
  recipes live in the docs and run under the `examples` dependency group. Nothing in
  `src/spoc` imports any of it.

### Decision: Settings-validation seam — Adopt pydantic (worked example only)

- **Status**: approved
- **Why**: app-owned `spoc.toml` tables reach the app already parsed on
  `framework.config.tables`, so plain-model validation (`Model.model_validate(table)`)
  is the exact fit. The docs contract stays tool-agnostic — "validate the parsed table
  with any schema validator" — and pydantic appears only as the worked example, pinned
  in the `examples` dependency group so the docs snippet test runs.
- **Considered**: pydantic-settings (its file/env source machinery duplicates reading
  the kernel has already done); dynaconf (its own mode/merge layering competes with the
  kernel's mode cascade); naming no tool (the docs example would be pseudocode).
- **Isolation**: documentation only — the kernel neither imports nor depends on it, and
  the seam works identically with any validator or none.

### Decision: Doc snippet execution — Adopt `pytest-examples`

- **Status**: approved
- **Why**: the "docs examples must run" bar is currently enforced for exactly one snippet
  (`test_settings_seam_docs_example_runs`); everything else can rot silently. pytest-examples
  (pydantic, MIT, Python 3.10–3.14) discovers examples in markdown and docstrings via
  `find_examples()`, runs them as ordinary pytest cases, and its `--update-examples` mode
  lints/formats snippets and inserts expected print output — which is precisely the
  FastAPI-style output-block habit the docs audit found missing. Library-style discovery
  (not blanket collection) lets snippets that need a project tree pair with the existing
  `spoc.testing` harness, and lets non-runnable fragments be either completed or explicitly
  skipped rather than silently ignored. Dev-dependency only — `dependencies = []` holds.
- **Considered**: mktestdocs (simpler, `memory=True` chains sequential blocks, but
  single-maintainer and no output checking or in-place updating); extending the existing
  docs-mirror test pattern by hand (zero new deps, but hand-writes discovery, extraction,
  and output comparison a maintained tool already ships — the `loc`/tokei mistake again).
- **Isolation**: one test module (`tests/test_docs_examples.py`) plus the docs dependency
  group. The docs themselves stay plain markdown; nothing in `src/spoc` is touched.

### Decision: API reference member lists — Adopt (configure) mkdocstrings/griffe `__all__` derivation

- **Status**: approved
- **Why**: the member lists in `api/public.md` and `api/tooling.md` are hand-enumerated, so
  a new `__all__` export silently vanishes from the docs. griffe — already this project's
  adopted API extractor (see "Public API surface extraction — Adopt griffe") and the engine
  under the already-installed mkdocstrings — treats `__all__` as the public-API authority
  natively: modules' exports populate from it, and the handler renders them without manual
  `members:` lists. This is configuration of two tools already adopted, not a new adoption,
  and it makes the docs and `apicheck` read the public surface from the same source of truth.
- **Considered**: keeping hand lists plus a CI drift-checker script (Build — polices a
  problem the adopted tool dissolves); a custom page-generation script over griffe's JSON
  dump (Build — reimplements the mkdocstrings handler).
- **Isolation**: the `::: module` option blocks inside `docs/docs/api/*.md` and the
  mkdocstrings handler config in `docs/mkdocs.yml`. No source changes; `__all__` remains
  the single declaration.

### Decision: CLI reference generation — Extend `mkdocs-macros` with a help-dump macro

- **Status**: approved
- **Why**: `tools/cli.md` is hand-written prose that can drift from the real argparse
  surface. The maturity rubric fails both purpose-built candidates (below), and the
  already-installed mkdocs-macros plugin accepts a ~20-line macro that imports the actual
  parser factory and injects each subcommand's `--help` text at build time — it cannot
  drift because it runs the real parser, and it adds no new dependency. The downward move
  from Adopt to Extend is justified by the candidates' immaturity and by the extension
  being glue over an adopted plugin, not a reimplementation of anything.
- **Considered**: mkdocs-argparse (purpose-built but tiny community, sparse documentation,
  unclear maintenance — fails the rubric on activity and community); mkdocs-rich-argparse
  (actively developed but targets rich-argparse parsers, which SPOC's plain zero-dependency
  argparse CLI is not).
- **Isolation**: the macros module referenced by `docs/mkdocs.yml` plus the placeholders in
  `tools/cli.md`. The CLI itself is untouched; the macro imports the parser factory the
  shipped console script already uses.
