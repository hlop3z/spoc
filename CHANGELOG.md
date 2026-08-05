# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) — with the 0.x caveat that a
**minor** bump is where breaking changes land until 1.0.0.

## [Unreleased]

### Fixed

- **Discovery ownership.** An instance or subclass of a decorated class inherits the
  `__spoc__` marker but is no longer treated as a declaration — a module-level
  `default_post = Post()` used to crash boot with a spurious `DuplicateComponentError`.
  The registry now also enforces one-object-one-identifier directly: a decorated instance
  imported into a second app keeps its first identity instead of registering twice. That
  short-circuit still validates the kind and segments it was handed, so identity reuse is
  not a way past the identifier grammar.
- **Error taxonomy at the boundaries.** An app declared in `spoc.toml` whose package does
  not exist raises `AppNotFoundError` instead of a raw `ModuleNotFoundError` (and
  `required=False` no longer excuses it); a plugin module that exists but fails to import
  propagates its own error instead of being misreported as absent; a malformed plugin
  reference or missing attribute raises the new `UnresolvedReferenceError` — including the
  empty-segment forms (`.attr`, `pkg..mod.attr`, `pkg.mod.`) that `importlib` answers with
  its own `ValueError` or `TypeError`; `[spoc.apps]`
  and `[spoc.plugins]` groups must be lists of strings (a bare string used to boot one app
  per character); an unknown `mode` — or an app list stranded under a misspelled one —
  fails start with `ConfigurationError` instead of silently installing nothing.
- **Lifecycle soundness.** A failed `start()` tears down the modules that did initialize
  and returns the framework to its inert pre-start state; `shutdown()` performs the same
  reset (fresh registry and loader, injected import path removed), so restarting on a
  different project no longer resolves stale components or grows `sys.path`. Ejecting is
  ownership-gated: `inject_apps` reports whether *it* inserted the entry, and only then
  does shutdown remove it — a second framework, or a caller who put the path there
  themselves, keeps it.
- **Scaffolder.** `spoc init BadName` exits with code 1 and a message instead of an
  unhandled traceback; committing into an existing empty directory is atomic (the
  directory is swapped out — and put back if the swap itself fails — or the per-file
  fallback rolls back its files and created directories on failure); a template using
  `$kind` outside a `per_kind` file is refused
  at validation instead of crashing mid-render with a `KeyError`.
- **CSV stays inside the JSON data model.** A row wider than the header is refused loudly
  instead of decoding to a `None`-keyed dict that re-encoded as corrupted output; the
  header is now the union of every row's keys (first appearance wins) instead of row 0's;
  non-tabular values are refused with a message naming the shape.
- **`collect()` failures stay in the `FormatError` family.** A file whose derived key
  violates the identity grammar now raises `CollectionError` naming the file, so
  `except FormatError` sees every way a collection can fail.
- Error messages without a module name no longer carry a trailing space, and the
  `spoc.formats.errors` docstring names `MissingDependencyError` correctly.

## [0.5.0] — 2026-08-04

SPOC is rewritten around a single idea: **the kernel describes and never executes.** Every
object a project defines gets one canonical identifier, the kernel holds a registry of them,
and every surface — HTTP routes, CLI commands, anything else — is a projection of that
registry rather than a second place to declare things.

This release supersedes the whole surface that shipped in 0.3.x. **No migration path is
provided**, and none is planned: the package has no users, so back-compat shims would cost
more than they could possibly save. If you are on 0.3.x, read
[the docs](https://hlop3z.github.io/spoc/) as if for the first time.

> **Note on version numbering.** `0.4.0` was set in `src/spoc/__about__.py` during development
> but never tagged or published to PyPI — no `0.4.0` distribution exists, and none will. The
> jump from `v0.3.9` to `v0.5.0` skips it deliberately so that a local checkout reporting
> `0.4.0` can never be confused with a released artifact.

### Added

- **`spoc init` — a project scaffolder**, shipped as the `spoc` console entry point. It
  generates a runnable project: config, framework declaration, one app with a module per
  declared kind, and an entry point, with all names agreeing by construction instead of by the
  reader keeping them in step by hand. The operation is fully checkable before a byte is
  written — the core validates names against the kernel's identity grammar, rejects path
  traversal, and builds a complete plan; the sink stages that plan in a temporary directory and
  commits it with `os.replace`, so a failure leaves the destination untouched rather than
  half-populated. Substitution is `string.Template`: name substitution and nothing else, no
  expressions to evaluate. Downstream frameworks can supply their own template sets through an
  entry-point group.
- **`spoc.formats` — a data sidecar** for reading, collecting, and addressing data. Five
  formats normalize to one JSON-shaped representation, so a project stops writing a loader per
  file and per format. Addressing is split by failure semantics rather than unified: RFC 6901
  JSON Pointer resolves exactly one value or raises naming the failing segment, while RFC 9535
  JSONPath returns a possibly-empty list — configuration reads must be loud, dataset queries
  legitimately match nothing. XML repetition is declared by path rather than inferred from
  occurrence counts, so a one-element document keeps the same shape as a many-element one.
- **`docs/architecture/kernel.md`** — the canonical Mermaid diagrams: system shape, identifier
  anatomy, resolution flow, and the kernel invariants.
- **`CONTRIBUTING.md`**, a project canon under `.canon/`, and a CI workflow that runs the
  canonical validation suite and gates releases on it.

### Changed

- **BREAKING — one identifier grammar.** Every object is addressed as
  `kind:namespace.object_name`, with each segment validated against `^[a-z][a-z0-9_]*$` at
  registration. Invalid segments are *rejected, never normalized*.
- **BREAKING — `Framework.resolve()` replaces `get_component()`.** Lookup fails per segment
  (kind → namespace → object_name), and each error names the segment, its value, and the valid
  candidates. There are no `None` returns anywhere in the lookup path.
- **BREAKING — one declaration object.** `Framework(*kinds, dependencies=, mode=)` is a pure
  declaration with no filesystem, `sys.path`, or import side effects; `start(base_dir)` boots
  the project, and `shutdown()` before `start` is a no-op. `framework.kind(name)` hands out
  registration decorators (an undeclared kind raises `UnknownKindError`), and
  `@framework.on_ready` registers callbacks that fire exactly once after discovery with the
  completed registry, before module init.
- **BREAKING — snake_case identifiers are derived from object names.** `@model class
  UserAccount` registers as `user_account`; PEP 8 class names need no restatement. Three
  boundaries stay strict so the kernel never guesses: an explicitly stated `name=` is used
  verbatim and never converted, the grammar module stays pure and strict, and *resolution never
  converts* — `resolve('models:blog.UserAccount')` fails. A derived name that cannot conform
  even after conversion (a class named `2Cool`) still fails loudly.
- **BREAKING — per-kind `required` replaces the framework-wide strict/loose switch.** Declaring
  a kind that only some apps implement no longer weakens the guarantee for every other kind.
  Absent and broken are now distinguished: a module that exists and raises is an error whatever
  its optionality.
- **BREAKING — per-kind `metadata` replaces the untyped `config={}` channel.** Field types are
  proved statically by `ty`, and the kernel asserts each instance matches its kind's declared
  type. A kind that states no contract accepts no metadata, which closes the escape hatch
  rather than renaming it.
- **BREAKING — `spoc.toml` is the only file the kernel reads.** `settings.py` is user-owned and
  never imported. Every `spoc.toml` key is optional with a default.
- **Discovery is loud.** Kind/module mismatches, invalid segments, and duplicate identifiers
  fail startup naming the object and its location, replacing the silent `type == module` filter.
- **The kernel is collapsed onto four boundaries.** Identity, declaration, and registry stay
  pure; the loader and config adapter touch the outside world; `Framework` is the only place
  they meet. The registry had been owned by the module importer — a pure core concern nested
  inside an adapter — which forced the loader to know what a kind is. `core/importer.py` is now
  `core/loader.py`. The kernel went from 1,823 to 978 lines (−46%) while tests grew.
- **No global state.** The loader is a plain class owning its registry, hooks, cache, and graph
  as instance state, so two `Framework`s can coexist and tests are isolated.
- **Dependency ordering uses stdlib `graphlib.TopologicalSorter`**, with `CycleError`
  translated to `CircularDependencyError`.
- **The published dependency set is still empty.** `dependencies = []` is unchanged. Both
  sidecars are quarantined: the kernel imports nothing from `spoc.scaffold` or `spoc.formats`,
  every scaffolder decision landed on the standard library, and every package the data sidecar
  adopts sits behind an extra that names itself when absent.

### Removed

- **BREAKING** — `get_component`, builder URIs (`app_object`), runtime `add_type`, and the
  `components` namespace view.
- **BREAKING** — `spoc.workers` (thread/process primitives) and `spoc.tools` (a second,
  parallel registry): the kernel describes and never executes, so both were out of scope.
- **BREAKING** — `spoc.types` and `spoc.utils` (trivial shims), `SingletonMeta`, and
  `singleton` — the global state the kernel no longer has.
- **BREAKING** — `Components` (internalized), `Schema`, `Hook`, `load_configuration`, and
  `DependencyGraph` from the public surface. `framework.on_startup` / `on_shutdown(kind)`
  replace `Schema.hooks`.
- The module-cache API, the never-read `on_startup_name` / `on_shutdown_name` options, empty
  subclass extension points, and a wildcard-regex hook engine that only ever answered "is this
  module's kind X?" — none had a caller.

### Fixed

- Acronym boundaries are split correctly when deriving snake_case names.
- Hook contract and loose-mode edge cases in the core.
- `default.toml` env fallback now loads regardless of the echo setting.

### Optional extras

Installing `spoc` bare reads JSON, CSV, and TOML — all standard library.

| Extra   | Installs                          | Enables                                    |
| ------- | --------------------------------- | ------------------------------------------ |
| `yaml`  | `ruamel.yaml`                     | YAML 1.2 read/write                        |
| `xml`   | `xmltodict`                       | XML read/write                             |
| `toml`  | `tomli-w`                         | TOML **writing** (stdlib `tomllib` reads)  |
| `query` | `python-jsonpath`, `iregexp-check`| RFC 9535 JSONPath + RFC 6901 JSON Pointer  |
| `full`  | all of the above                  | everything                                 |

[Unreleased]: https://github.com/hlop3z/spoc/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/hlop3z/spoc/compare/v0.3.9...v0.5.0
