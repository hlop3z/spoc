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

### Decision: Keyword-safe decorator names — Adopt the standard (PEP 8 + stdlib `keyword`)

- **Status**: approved
- **Why**: `spoc init --kinds class` generated `class = framework.kind("class")`, which
  does not parse. The concern reads as "turn a category name into a legal identifier",
  which sounds like an inflection problem and is not: singularization is already decided
  and deliberately conservative, and the half that was broken is answered by a convention
  Python publishes about itself — PEP 8's *"single trailing underscore … to avoid
  conflicts with Python keyword, e.g. `class_`"*. Detection is `keyword.iskeyword`, the
  authoritative list, from the standard library, already imported in the module. Adopting
  the standard costs one helper; a reader who has met `class_` needs no explanation.
- **Considered**: an inflection library (`inflect`, `inflection`) — solves the half that
  is not broken, escapes no keywords, and cannot be adopted at all while the
  distribution's `dependencies = []` is an invariant; refusing keyword kinds at validation
  — would make the scaffolder stricter than the kernel it scaffolds for, since the
  identity grammar accepts `class` and the registry stores it happily; a prefix
  (`kind_class`, `_class`) or a rewording (`klass`) — both inventions, and a leading
  underscore additionally reads as private.
- **Isolation**: `_escape_keyword` and `decorator_names` in `src/spoc/scaffold/core.py`.
  The templates interpolate `$decorator` and never spell a name themselves, so no template
  changed.

### Decision: Collisions introduced by escaping — Build (thin), append underscores

- **Status**: approved
- **Why**: escaping can create a duplicate the pre-escape check cannot see — kinds `class`
  and `class_` both reach `class_`, and the declaration would bind one variable twice with
  the second silently winning, handing one kind the other's decorator. A final pass that
  appends underscores until each name is unused is total, terminates, extends the
  convention already adopted above rather than inventing a second one, and does nothing at
  all on inputs that do not collide.
- **Considered**: raising an error on the collision (refuses a legal pair of kinds for a
  cosmetic reason, against the function's own stance that a working file beats a pretty
  variable); numbering duplicates `class_2` (a second scheme where extending the first one
  reads correctly).
- **Isolation**: the loop inside `decorator_names`. Order comes from the declared kinds
  tuple, so the result is deterministic.

### Decision: Verifying platform-conditional behavior — Extend the cache-location build, platform as a value

- **Status**: approved
- **Why**: this re-examined *Cache location — Build (thin) on the platform conventions* above and
  confirmed it: `platformdirs` is still the mature answer, no standard-library equivalent has
  landed (the discuss.python.org thread remains a discussion, not a PEP), and `dependencies = []`
  still blocks it. What changes is only *how* the already-built fifteen lines are shaped.
  `default_cache_root()` splits into a pure function over an explicit platform identifier and
  environment mapping, plus a thin adapter reading `sys.platform` and `os.environ`. Branch
  selection stops being an ambient effect and becomes a value, so every arm is reachable from
  every host by ordinary parametrization — which is what the `platform-support` capability
  requires and what makes the coverage figure stop being a property of the machine that produced
  it.
- **Considered**: the pytest platform plugins (`pytest-platform-markers`, `pytest-skip-markers`)
  — mature and actively maintained, but they *skip* tests on the wrong platform, which is the
  categorical opposite of the requirement; adopting either would defeat it. Monkeypatching
  `sys.platform` per test — no production change, but it patches a global other code may have
  already read and leaves selection ambient.
- **Isolation**: the pure function is core; the reader is the adapter, behind the `Cache` port.
  The earlier ADR's "swapping to `platformdirs` later changes one adapter" gets strictly easier,
  not harder.

### Decision: Retention key for a revision — Adopt `hashlib`, Extend the existing digest scheme

- **Status**: approved
- **Why**: the revision reaches the cache as a path segment, and today it is filtered to path-safe
  characters with any empty result becoming the literal `invalid`. Both halves are lossy:
  `feature/x` and `featurex` land on one entry, and every unusable revision lands on `invalid`
  together — two distinct revisions sharing retained content, which is the one thing a cache keyed
  by an immutable revision must never do. The mapping becomes verbatim when the revision is
  already a safe segment, `rev-<sha256 truncated>` otherwise, and a refusal when it is empty.
  Total, collision-free to the strength of the digest, incapable of traversal, and it extends the
  `url-<digest>` scheme `HttpRevisionResolver` already uses rather than inventing a second one —
  the same move the *Collisions introduced by escaping* decision above made, for the same reason.
  Hashing is on the never-hand-roll list; `hashlib.sha256` is the standard library's answer and is
  already imported in `remote.py`.
- **Considered**: refusing every non-path-safe revision — strictest and simplest, but the revision
  is not always the caller's to control, since it can arrive as a `sha` field in a server's
  response, so it converts a server's oddity into the user's error; rejected on the same reasoning
  the escaping-collision decision used to decline refusing a legal input. Percent-encoding —
  reversible and total, but puts `%` in path segments on the platform where this cache is least
  tested, and changes the key for revisions that are safe today.
- **Isolation**: `DirectoryCache._entry` in `src/spoc/scaffold/cache.py`. Every revision reachable
  through the reference grammar today is already path-safe, so no retained content is invalidated.

### Decision: Evidence that the retention key is injective — Adopt Hypothesis

- **Status**: approved
- **Why**: "two distinct revisions never share retained content" is an injectivity property over an
  open input domain, and hand-picked examples can only ever demonstrate the cases someone thought
  of — the `feature/x` collision survived precisely because nobody picked it. Hypothesis is already
  a dev dependency and already carries this project's property suite, including stateful machines,
  so this adopts an instrument that is present rather than adding one. The hand-picked cases stay
  as named regression anchors for the collisions actually found.
- **Considered**: table-driven examples alone (cheaper to read, but proves only the chosen rows);
  adding a dedicated fuzzing tool (a second instrument where the adopted one already fits).
- **Isolation**: `tests/test_properties.py` for the property, `tests/test_scaffold_cache.py` for
  the named regressions.

### Decision: Provoking the concurrent-retention race — Adopt pytest's `monkeypatch` at the seam

- **Status**: approved
- **Why**: `Cache.retain` catches a failed publish and accepts the entry if another process
  published the revision first. Injecting that failure at the publish seam, with the entry
  pre-created, exercises the branch deterministically — no sleeps, no scheduler dependence — along
  with the negative case where the entry does not exist and the failure must still raise. No tool
  is being chosen here beyond the test framework already in use; recorded because the alternative
  is the kind that quietly becomes the suite's one flaky test.
- **Considered**: two real threads on a barrier — exercises the true interleaving, but is
  timing-dependent and would be the only nondeterministic test among 685; kept out of the gate.
- **Isolation**: `tests/test_scaffold_cache.py`. Acknowledged limit: this verifies the handler, not
  that the underlying rename is atomic on every filesystem — which the multi-platform gate now at
  least executes for real on each declared platform.

### Decision: Coverage floor — Adopt `coverage.py` reporting, decline the gate

- **Status**: approved
- **Why**: no `fail_under` is introduced. The lines that mattered in this change were invariant
  lines — a transfer bound, a redirect refusal, an aliasing key — and a floor cannot tell those
  from any other line, so it would make a number the target on the change that exists to argue
  against treating it as one. What replaces it is the `platform-support` requirement that the
  measurement no longer depends on its host, which is what makes two runs comparable at all.
  Coverage gets a row in `.canon/checks.md` marked a review aid rather than a gate, the same
  treatment `tokei` already carries.
- **Considered**: a global `fail_under` at the achieved total — cheap, standard, and would catch
  silent erosion; declined for this change and left live rather than closed. If erosion is observed
  later, the argument changes and this gets revisited.
- **Isolation**: `[tool.coverage.report]` in `pyproject.toml` and the review-aid row in
  `.canon/checks.md`.

### Decision: Multi-platform execution of the gate — Rent, on the CI platform already in use

- **Status**: approved
- **Why**: infrastructure, so the hierarchy answers it without further evaluation; the runners are
  rented from the CI platform this project already uses. The substantive part is scope, not vendor:
  the declared platform set becomes Linux, Windows, and macOS, replacing
  `Operating System :: OS Independent` — a claim no gate can satisfy — and the `python` job runs
  the full product of three operating systems and three interpreter versions with no exclusions.
  `cache.py` carries a darwin arm today, so a set omitting macOS would ship a branch no gate ever
  executes. The repository is public, so the added legs cost queue latency rather than money.
- **Considered**: excluding OS/version combinations to trim the matrix — cheaper, but the matrix
  stops being derivable from a single statement in `.canon/checks.md`, which is the property that
  keeps `task check` and CI the same gate. Linux and Windows only — covers the dev/CI split that
  produced the recent encoding defect, but leaves the darwin arm unexecuted.
- **Isolation**: the `python` job matrix in `.github/workflows/ci.yml`, derived from the platform
  scope stated in `.canon/checks.md`. The `go`, `docs-build`, and `doc-links` rows stay
  single-platform, which the capability permits for checks whose outcome cannot differ by platform.

### Decision: Type-reference extraction for stub generation — Build on stdlib

- **Status**: approved
- **Why**: the describe pass holds the *live* registered objects, so `__module__` /
  `__qualname__` and `inspect.signature` answer the question directly and exactly. Every
  candidate tool reads source statically — the wrong side of the boundary: a static reader
  would re-derive what the registry already knows, and could not see components registered
  through `[spoc.plugins]` at all, since those exist only after configuration is resolved.
  This is a Build decision, justified by the absence of any tool that consumes a runtime
  registry rather than a source tree. Scope is small and stdlib-only, so the
  zero-runtime-dependency invariant holds without an extra.
- **Considered**: extending griffe, this project's already-adopted API extractor (static
  source analysis, blind to config-registered components, and duplicating knowledge the
  registry holds); adopting mypy `stubgen` (mature, but generates from module structure with
  most types defaulting to `Any`, and cannot emit registry-derived `Literal` overloads —
  a different problem).
- **Isolation**: one extraction module inside `src/spoc/stubs/`, consumed only by the
  describe pass. Nothing in `src/spoc/core/` or `src/spoc/framework.py` imports it.

### Decision: Stub emission and byte-stable formatting — Build the emitter, Adopt ruff

- **Status**: approved
- **Why**: the emitter is a pure function over our own manifest IR — roughly one stdlib
  module — and no tool can generate it, since the overload set is derived from a booted
  registry. Everything around it is rented from a tool already in the repo: byte-stability
  comes from `ruff format`, and stub-specific linting comes free by enabling ruff's `PYI`
  rules, which vendor flake8-pyi. Net new dependencies: none. Determinism is then a property
  of the formatter rather than of hand-written alignment logic.
- **Considered**: hand-rolling formatting inside the emitter (full control, but re-implements
  normalization a formatter already in the toolchain performs correctly — the `loc`/tokei
  mistake shape); adopting `stubgen` for a base stub and injecting overloads afterwards (two
  sources of truth for one file, and stubgen's `Any`-defaulting output would need rewriting
  more extensive than emitting from scratch).
- **Isolation**: `emit(manifest) -> str` stays pure; the formatter is invoked through the
  file-writing adapter in `src/spoc/stubs/`, and the `PYI` rule selection lives in
  `[tool.ruff.lint]` in `pyproject.toml`.

### Decision: Stub conformance verification — Adopt `assert_type` under mypy, pyright, and ty

- **Status**: approved
- **Why**: the feature's entire promise is that a type checker resolves the promised type, so
  the gate must be run by the checkers users actually run. CI today runs only `ty`, which is
  beta at `0.0.x` with an explicit upstream warning to expect bugs, missing features, and
  fatal errors, and which no editor runs by default — a stub could pass CI and fail every
  user. The verification is a fixture project of `typing.assert_type` assertions over the
  generated stub, checked under all three: mypy and ty for `assert_type`, pyright with
  `reveal_type(expr, expected_text=...)` for the exact rendered type. This mirrors how the
  Python typing specification's own conformance suite is written, so it stays portable if a
  fourth checker matters later.
- **Considered**: mypy `stubtest` — purpose-built for stub/runtime drift, but wrong here on
  two counts: it introspects the runtime and would flag the generated `_Root` class, which
  deliberately does not exist at runtime, and it documents that it cannot verify a return
  type is accurate, which is precisely the claim being made. Restricting the matrix to mypy
  and pyright (drops beta-checker noise, but loses early warning when ty regresses on stubs
  while ty remains this project's own gate).
- **Isolation**: one fixture project plus one CI job; the three checkers are dev-group
  dependencies only and nothing in `src/spoc` imports them. `ty` remains the checker for
  ordinary source; the two additions check the generated stub, not the library.

### Decision: IDE autocomplete verification — Adopt pyright as the proxy

- **Status**: approved
- **Why**: Pylance, the extension supplying completion in VS Code, is built on pyright, so
  pyright resolving a type correctly *is* the evidence that completion works — there is no
  separate Pylance behavior to test. `reveal_type(expr, expected_text=...)` asserts the
  rendered type a hover would show, which is the closest programmatic analogue to what the
  user sees. A one-time manual check in VS Code is recorded in the docs so the human-visible
  claim has been observed at least once by a person.
- **Considered**: driving a real `pyright-langserver` LSP session and asserting on returned
  completion items (proves the end-user experience literally, but adds a heavy and
  flake-prone harness to determine something pyright already decides); a manual smoke test
  alone (cheapest, but nothing then prevents a silent regression).
- **Isolation**: the same fixture project and CI job as the conformance decision above; the
  manual check is a documented step, not a gate.

### Decision: Namespace-collision model — Adopt Django's app-label contract, build the check

- **Status**: approved
- **Why**: Django solved this exact problem with this exact derivation. `AppConfig.label`
  defaults to the last component of the app's dotted path, and two apps resolving to one
  label raise `ImproperlyConfigured: Application labels aren't unique, duplicates: <label>`
  at startup; the documented fix is a custom `AppConfig` stating an explicit `label`. The
  model — derive by default, fail loudly on contest, allow an explicit override — is what
  is adopted. The *code* is built, because there is nothing to install: the enforcement is
  a `dict[str, str]` from namespace to owning package inside `Framework`, and it is domain
  logic about SPOC's own identifier grammar (Rule 11), not a general concern any library
  could hold. One improvement on the precedent: Django's error names the duplicated label
  but not which apps produced it — a recurring complaint in its issue tracker — so ours
  names the namespace *and* both claiming paths.
- **Considered**: auto-disambiguating a collision by prefixing the parent segment
  (`vendor_shop`) — rejected because a component's identity would then change depending on
  which other apps happen to be installed, which is a worse failure than the one being
  fixed. Leaving the merge and relying on the existing duplicate-identifier error — rejected
  because that error only fires when object names also coincide, and names a third place
  when it does.
- **Isolation**: one ownership map built in `Framework._register_apps` before any import,
  consulted by `_register_plugins`. No new module, no dependency, no public type.

### Decision: Explicit-namespace syntax — Adopt Python's `as` convention, build the split

- **Status**: approved
- **Why**: `"vendor.shop as vendor_shop"` reuses the language's own vocabulary for rebinding
  a name to avoid a clash, so there is nothing new to learn — the DX bar this project holds.
  It also avoids overloading `:`, which already means "attribute" in `module.path:attribute`
  (the `--framework` reference and the plugin reference form). Parsing is a split on ` as `
  with surrounding whitespace, which a dotted module path cannot contain; a parser library
  for this would be more code to configure than to write, and would be the `loc` mistake
  again.
- **Considered**: a separate `[spoc.namespaces]` table (explicit, but puts the alias far
  from the entry it modifies, so a reader consults two places to learn one app's namespace);
  a `:` suffix (consistent punctuation, but `:` already means "attribute" in this project's
  own reference syntax, so it would make one delimiter mean two things).
- **Isolation**: parsed once where app entries are read, immediately validated by the
  existing `validate_segment("namespace", …)`, so the grammar keeps one enforcement point.

### Decision: Per-app metadata location — Adopt Django's central app list, refuse a colocated manifest

- **Status**: approved
- **Why**: Odoo carries roughly thirty keys in a `__manifest__.py` beside each addon, and it
  needs to: addons are acquired and installed independently of the project, so the manifest
  is how a package the project did not write states its own facts. SPOC has no third-party
  apps. Every app in every known project is written by whoever writes `spoc.toml`, so the
  facts a manifest would carry — inter-app dependencies, external requirements, framework
  version compatibility — are already known at the one place they would be read. Django,
  whose app model this project otherwise follows, has run twenty-one years on a single list
  of strings in `INSTALLED_APPS`: no per-app manifest, no per-app dependency declaration,
  ordering needs met by declaration order plus a load-phase barrier. The asymmetry that
  settles it is in our own release policy: the pre-stable allowance ends at the first stable
  major release and cannot be extended, after which a configuration key can always be added
  and can never be removed. A key added speculatively is an obligation for the life of the
  project; a key added on demand costs one minor release.
- **Considered**: a colocated `manifest.toml` per app (correct ownership — an app's author
  states the app's facts — but there is no third-party app to own anything yet, and it adds
  a second configuration location against the one-file simplicity this project holds);
  `[spoc.app.<name>]` tables inside the existing `spoc.toml` (cheapest carrier and keeps one
  file, but puts an app's own facts in the consumer's configuration, which is the wrong
  owner the moment third-party apps exist — so it would have to be replaced rather than
  extended, which is the worst of both); entry points advertising apps from installed
  distributions (the mechanism this project already uses for scaffold templates and the
  pytest plugin, and the right answer the day apps ship separately — recorded here as the
  preferred future form so the question starts from it rather than from Odoo's manifest).
- **Revisit when**: an app is distributed separately from the project that installs it. That
  is the single fact this decision waits on; until it is true there is no owner for the file.

### Decision: Per-app framework-version compatibility — Rent the packaging ecosystem's check

- **Status**: approved
- **Why**: Odoo's `adapt_version`/`check_version` refuse an addon whose release series does
  not match the running Odoo, setting `installable = False`. Odoo needs that because an
  addon arrives independently of the install and nothing else in the pipeline can catch the
  mismatch. A SPOC app lives inside the project that depends on SPOC, so the project's own
  dependency pin already is the check — enforced by the installer before any code runs,
  which is earlier and more precise than a boot-time comparison could be. Renting beats
  building here twice over: the packaging ecosystem already resolves version constraints,
  and reproducing that inside the kernel would require PEP 440 comparison, which the
  zero-runtime-dependency invariant forbids adopting `packaging` for and which hand-rolling
  would repeat the `loc` mistake — epochs, pre-releases, and local versions are precisely
  where a hand-written comparator is quietly wrong.
- **Considered**: `requires-spoc = ">=0.8,<0.9"` in a per-app manifest (needs the version
  comparison above, and depends on the manifest refused in the preceding decision); checking
  the major segment alone as an integer (avoids PEP 440 entirely and is honest about what it
  verifies, but what it verifies is exactly what the dependency pin already verified); a
  boot-time warning rather than a refusal (a diagnostic nobody reads, and the project's rule
  is loud failure or nothing).
- **Revisit when**: apps ship independently — the same trigger as the preceding decision,
  because this check only has work to do when the app and the framework are acquired
  separately.

### Decision: The load-ordering guarantee — Extend `graphlib` with an explicit `(kind_depth, app_index)` key

- **Status**: approved
- **Why**: CPython defines `static_order()` as the `get_ready()`/`done()` loop, so the
  cross-app kind-phase barrier is documented behaviour rather than an accident. Within a
  level the documentation promises nothing — only that the order "may depend on the specific
  order in which the items were inserted in the graph", which is a caveat, not a contract.
  The app-list tiebreak is exactly that unpromised half, and it holds today only because
  `Framework._register_apps` happens to insert app-major. Sorting by `(kind_depth,
  app_index)` moves the guarantee into code a reader can check, and satisfies every edge by
  construction because `depends_on` runs only from a lower depth to a higher one. The shape
  is standard: Odoo's module graph sorts by `(phase, depth, order_name)` and networkx
  exposes the same idea as `lexicographical_topological_sort(key=…)`.
- **Considered**: adopt `graphlib` as-is and document the level-order behaviour (zero code
  change and not wrong, but the guarantee then holds for a reason invisible in our source);
  canonicalise graph insertion order so `static_order()` yields the intended sequence (makes
  the artifact deliberate instead of replacing it);
  `networkx.lexicographical_topological_sort(key=…)` (precisely the primitive wanted, mature
  and well documented — hard-rejected on the zero-runtime-dependency invariant, not on
  quality).
- **Scope — borrow the idea, not the library**: what is taken from networkx is the premise
  behind `key=`, that a topological order with a stated tiebreak is a sort by an explicit
  key. What is not taken is anything amounting to a graph library — no general graph type,
  no traversal API, no path or reachability helpers. It is one two-element tuple over data
  the kernel already holds, and a `sorted()` call. A future need for general graph
  algorithms is the signal to revisit this and adopt one, not to grow this.
- **Isolation**: `Loader.ordered()`, the one method turning the module graph into a
  sequence. Graph construction is untouched and nothing else in the kernel learns what a
  kind depth is.

### Decision: Cycle detection in the kind graph — Adopt `graphlib`, unchanged

- **Status**: approved
- **Why**: an ordering key sorts a DAG but cannot notice that the graph is not one.
  `graphlib.TopologicalSorter.prepare()` already detects cycles and reports one with its
  first and last node identical, which is what `CircularDependencyError` names today.
  Keeping it means the sort key never has to prove acyclicity and the error contract does
  not move. Both candidates for the ordering decision above were standard library, so the
  zero-runtime-dependency invariant was never in tension — that gate turned on ownership of
  the guarantee, not on acquiring anything.
- **Considered**: detecting cycles inside the depth computation (a longest-path walk can
  find a back edge, but it restates `prepare()` and would have to reproduce the cycle report
  the existing error message is built on); no detection, trusting declaration validation (a
  cycle becomes unbounded recursion or a silently truncated order — the rule here is loud
  failure or nothing).
- **Isolation**: unchanged — the `except graphlib.CycleError` clause in `Loader.ordered()`.

### Decision: The registry projection's schema — Adopt JSON Schema 2020-12, hand-written

- **Status**: approved
- **Why**: Rule 9 settles the language; the gate had to settle authorship and the draft.
  Pinned to `https://json-schema.org/draft/2020-12/schema` — the current published draft,
  where its successor is still an unexpired IETF Internet-Draft and could yet change. The
  schema is hand-written and checked in because the change's design makes the *document* the
  format and the Python dataclass one producer of it; a generator inverts that authority.
  Generation also cannot express what carries the most meaning — the
  `kind:namespace.object_name` pattern, the closed shape vocabulary, and a format version
  independent of the release version — without annotating the dataclass into a schema DSL,
  which is the same inversion by another route.
- **Considered**: `dc_schema` (tiny, stdlib-only, emits 2020-12 — the closest fit if
  generation were wanted; micro-library with thin maintenance signal, and it inverts the
  design's Decision 2); pydantic (mature, 2020-12 capable, but it lives in the `examples`
  group and this would promote it to a build-time dependency of the published artifact);
  draft 07 (broadest legacy support, rejected as legacy for a format meant to outlive the
  implementation).
- **Drift control**: hand-authoring is a restatement, and it is paid for by verification
  rather than generation — every projection the suite produces is validated, a malformed
  document is asserted to fail, and a parity test asserts the producer's field set equals
  the schema's `properties`/`required` keys.
- **Isolation**: the published schema file and the projection module that produces the
  document. Nothing in the kernel imports a validator.

### Decision: Validating the projection in the suite — Adopt `jsonschema`, dev group only

- **Status**: approved
- **Why**: Standard-format validation is on the never-hand-roll list, so the question is
  which validator, never whether to write one. `jsonschema` (python-jsonschema, 4.26.0,
  January 2026) is the reference implementation, fully supports 2020-12, and is pure Python
  — so it installs across the whole gated platform matrix without a wheel question. Dev
  group only, on the same precedent as `hypothesis` and `pytest-examples`: `dependencies`
  stays empty and no downstream framework inherits it.
- **Reconciles with the earlier rejection**: "Configuration validation — Adopt `tomllib`,
  build the four-key check" rejected `jsonschema` for pulling four transitive dependencies
  to describe a four-key contract. That rejection stands. It was a *runtime* dependency
  there and is a *test* dependency here, so the zero-`Requires-Dist` invariant behind it is
  untouched; and that ADR scoped Rule 9 to "contracts and identifiers exchanged with the
  outside world, not a four-key internal config file" — the registry projection is exactly
  such a contract, which is why the same rule now points the other way on the same tool.
- **Considered**: `jsonschema-rs` (Rust-backed, much faster; throughput is irrelevant for a
  suite validating small documents, and a compiled extension adds wheel risk across three
  OSes and three Python versions); `check-jsonschema` as a command in `.canon/checks.md`
  (matches the tokei/`ensure` precedent, but the suite builds projections in `tmp_path` and
  a CLI forces file marshalling for every case, including the negative ones).
- **Isolation**: the test module asserting conformance. No source module imports it, and the
  schema file stays validatable by any external tool.

### Decision: A domain vocabulary for the projection — none applies

- **Status**: approved
- **Why**: Rule 9 points at Schema.org/RDF for vocabularies, so the question was asked and
  the answer is negative: nothing standard describes *what an application registered
  in-process*. Schema.org `SoftwareApplication` describes software products for search and
  discovery; SPDX (ISO/IEC 5962) and CycloneDX describe dependency inventories keyed by
  Package URL for licence compliance and supply-chain use; OpenAPI and AsyncAPI describe API
  surfaces. Each models a different subject, and adopting one would bend this format to an
  ill-fitting vocabulary for interoperability no consumer would exercise. JSON Schema alone
  is the whole of the adoption.
- **Recorded so it is not re-asked**: the negative answer is the deliverable. The revisit
  trigger is a change of *subject*, not of scale — if the projection ever describes packages
  rather than in-process components, adopt CycloneDX plus purl at that point.
- **Considered**: aligning field names with Schema.org properties for familiarity (buys no
  interoperability while constraining naming; `shape` has no analogue at all).
- **Isolation**: not applicable — nothing is adopted.

### Decision: Serializing the projection — Adopt the standard library's `json`

- **Status**: approved
- **Why**: Standard-format serialization is on the never-hand-roll list and the standard
  library covers it, so there is nothing to acquire. It also holds the containment boundary:
  `spoc.formats` is a contained subpackage the kernel never imports, and the kernel's own
  surfaces already use stdlib `json` directly — `scaffold`'s provenance and remote-template
  modules are the existing precedent. Routing the projection through `formats` would make an
  optional-extra subpackage load-bearing for a core surface.
- **Considered**: `spoc.formats` (rejected on the containment boundary, not on capability);
  a third-party JSON encoder (nothing to gain, and `dependencies` stays empty).
- **Isolation**: the projection module's emitter, with a test pinning the boundary.

### Decision: A kernel lifecycle's state transitions — Build, hand-written flags under one lock

- **Status**: approved
- **Why**: `dependencies = []` is an enforced invariant, so a runtime state-machine library is
  architecturally incompatible — the hierarchy's own stated ground for Build. The machine has
  three states (inert, started, transitioning) and the `harden-failure-paths` change adds two
  failure edges to it; an adopted framework would be larger than what it models. The defect
  being fixed was never the representation, it was that the reset obligation lived in four
  places instead of one.
- **Considered**: `python-statemachine` 2.6.0 (released 1 Aug 2026, Production/Stable, guards
  and validators, full async support — the strongest option on merit, and it would be the
  kernel's first runtime dependency); `transitions` (long-standing, lightweight, extensible;
  same fatal objection).
- **Revisit trigger**: states beyond inert/started/transitioning, or conditional transitions.
  The objection is the dependency invariant plus current size, not the libraries' quality.
- **Isolation**: the private transition helper in `framework.py` — the one place the flags and
  the lock are touched.

### Decision: Exercising a race in the test suite — Extend the existing pattern with `threading.Barrier`

- **Status**: approved
- **Why**: test-only, so the runtime dependency invariant does not bind, and the stdlib
  primitive is what the official Python free-threading guide recommends for this exact job —
  a barrier before the suspected line releases the workers together. It exists because
  `test_racing_duplicates_have_one_winner` called `.result()` on each submission before
  submitting the next, so its two "racing" threads never overlapped and the test passed for
  twenty iterations without testing a race at all. The lesson generalizes: a concurrency test
  must *establish* the overlap, never assume it.
- **Considered**: `blanket` (deterministic concurrency testing — wraps threading primitives and
  drives execution from the main thread so a test chooses which thread takes the lock next;
  better for inherently probabilistic races, but it intercepts threading primitives and is
  new); `pytest-run-parallel` (Quansight-Labs; runs one test in many threads — strong for
  broad thread-safety sweeps, cannot express "these two operations must overlap").
- **Outcome**: the barrier repaired the duplicate race, and the escalation to `blanket` was
  not needed for the resolution-failure guarantee either — but not because a barrier
  sufficed. The store only ever grows, so a multi-observation failure could only name
  candidates that appeared *after* the lookup, and exposing that requires suspending
  execution *inside* `resolve` between the lookup and the candidate scan, which no barrier
  placed outside it can reach. Counting lock acquisitions instead pins the mechanism
  exactly and deterministically. Recorded because "adopt the deterministic tool" was the
  anticipated answer and a deterministic *assertion* turned out to beat it.
- **Revisit trigger**: a concurrency test that cannot be made reliable with a barrier and has
  no deterministic invariant to assert instead. Adopt `blanket` for that test rather than
  tolerating flakiness or deleting the coverage.
- **Isolation**: `tests/test_concurrency.py`. No barrier appears in `src/`.

### Decision: Logging from a zero-dependency library — Adopt the standard library's `logging`, bridgeable but unbridged

- **Status**: approved
- **Why**: stdlib `logging` is the mature standard for a library's position in the stack. The
  canon's never-hand-roll rule points at OpenTelemetry for observability, and the 2026 guidance
  resolves the apparent conflict rather than overriding it: a *library* emits to a named logger
  and the *application* owns the telemetry pipeline. Three consequences are taken deliberately:
  a `NullHandler` on the `spoc` root logger, because otherwise Python's `lastResort` handler
  prints WARNING and above to stderr and any error-level log ships as noise to every
  application that never configured logging; `getLogger(__name__)` everywhere, replacing a
  hardcoded `getLogger("spoc")` that coexisted with the `__name__` convention and denied
  consumers per-subsystem control; and lazily-formatted `%s` arguments with `exc_info=True`
  rather than pre-formatted text, which is what makes records OTel-bridgeable *without* an OTel
  dependency — an application routing them through `LoggingHandler` gets a structured
  exception record with attributes instead of a string to parse back apart.
- **The logger-name contract**: `spoc` is the stable handle a consumer configures. Names below
  it follow module paths and are internal, so relocating a module is not a silent breaking
  change for someone's logging config. Recorded now to stop logger names becoming an
  accidental part of the public surface.
- **Considered**: bridging to OpenTelemetry in the library (needs an intercept layer plus OTel
  packages — a runtime dependency for a concern the consuming application owns); `structlog`
  (better structured-logging ergonomics, still a runtime dependency).
- **Isolation**: one `NullHandler` registration at the package root; every module keeps its own
  `__name__` logger and nothing else touches logging configuration.

### Decision: Tiering the downstream command mount points — Provisional, all four of them

- **Status**: approved — raised 2026-08-12, decided 2026-08-12 in `tier-command-mount-points`
- **Why**: `init`, `app`, `check`, `list`, `explain`, `stubs`, and `projection` all mount into a
  caller's own `argparse` parser through a `register` function, and that is how a framework built
  on SPOC publishes them under its own command name. The mechanism is deliberate — `derive_kinds`
  and `source_factory` exist precisely so a downstream composition root can supply them — but each
  `register` was exposed only from a plain module, which under the derivation rule makes it
  `internal`: no promise, removable in a patch. Meanwhile `ENTRY_POINT_GROUP` is exported and
  `template-set:default` is listed public, so a framework author was *promised* the template path
  and *not* the command path. Half a guaranteed extension point is worse than neither, because the
  unguaranteed half is the one that most looks like an invitation. Each `register` is now
  re-exported from its package with a provisional notice, and the general rule — an extension
  point's parts carry coherent tiers — is now a requirement in `public-api-surface` rather than a
  thing someone happened to notice.
- **Widened from one mount point to four**: the question was raised against `scaffold.cli.register`
  alone, because that is where the public half of the path lived. Inspection found `diagnostics`,
  `projection`, and `stubs` expose a structurally identical function, all four `internal`, all four
  mounted by `spoc.cli` and by nothing else. Promoting only the scaffolder would have left a
  framework author with `hello init` promised and `hello check` not — the same defect one level
  down. The Django-admin line the how-to already draws settles it: `django-admin` is `startproject`
  *and* `check`, and a downstream CLI that can generate but not validate is half a CLI. One path,
  one decision (Rule 7).
- **Why `provisional` and not `public`**: the signature takes `argparse._SubParsersAction`, a
  private standard-library type. Promising it in perpetuity would commit SPOC *and every downstream
  framework* to `argparse`, so a later move to another parser would either be blocked or force a
  major release for a reason unrelated to the kernel. `provisional` states exactly what is true:
  publicly documented, intended for this use, unsettled in shape, breakable in a minor but never in
  a patch. Each notice names two settling conditions — a framework outside SPOC actually mounting
  it, which fixes the shape against a real second caller, or SPOC committing to its parser choice.
- **Considered**: leaving all four `internal` and relying on the how-to's warning (honest, but makes
  a documented extension point unusable by anyone unwilling to pin an exact version — the whole
  downstream story); promoting to `public` behind a SPOC-owned mount protocol instead of argparse's
  type (the durable answer, and still the right one later — deferred because designing that type now
  means designing it against an imagined caller rather than a real second one); exposing the
  commands as data for each framework to build its own CLI from (largest change, makes the parser
  choice entirely downstream — worth revisiting only if the protocol option is taken).
- **Isolation**: no signature changed and no behavior moved. `cli.py` remains a thin adapter in all
  four packages; the promotion states a promise about an adapter that already had the right shape.
  Two import edges were redirected so a package can publish its own adapter without a cycle:
  `projection.cli` now imports `dumps`/`project` from the modules defining them, and `stubs.cli`
  defers its import of `generate`/`verify` into the handler — which also means mounting a command
  no longer loads the machinery behind it. `spoc.cli` now reaches all four through the published
  path rather than the internal module path, so the shipped program is a consumer of the extension
  point rather than a privileged second assembly of it.
