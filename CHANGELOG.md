# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) — with the 0.x caveat that a
**minor** bump is where breaking changes land until 1.0.0.

What each version increment promises, and for which parts of the surface, is written
down in [Stability & Versioning](https://hlop3z.github.io/spoc/api/stability/).

## [Unreleased]

### Added

- **A stability contract.** Every element of the published surface — importable names,
  the `spoc` command, the pytest plugin and its fixtures, the extras, the `spoc.toml`
  schema, and the template set format — now carries exactly one tier: `public`,
  `provisional`, or `internal`. The tiers are declared in `[tool.spoc.stability]` in
  `pyproject.toml`, and the docs page, the provisional notices in docstrings, and the
  checker are all projections of that one table.
- **`spoc.component`.** The low-level marker was only reachable as
  `spoc.core.declaration.component`, which the docs told you to import even though
  `spoc.core` is internal. It is now re-exported at the top level. The old path still
  works but is internal and carries no promise — use `from spoc import component`.
- **`apicheck`**, a workshop tool (`cd scripts/py && uv run apicheck ../..`) that fails
  when the surface exposes something the manifest does not declare, when the manifest
  declares something the surface no longer exposes, or when a `provisional` element
  fails to say so in its own docstring. It runs in the same gate as the tests.
- **A deprecation signal** following PEP 702 — `warnings.deprecated` on 3.13+, with a
  stdlib-only fallback on 3.12. `dependencies` stays empty.

### Changed

- **`spoc.core` is internal, explicitly.** Its docstring previously described it as
  "reachable for anyone extending the kernel," which read as a promise it never made.
  Nothing in it is stable, however reachable it is.
- **This supersedes the 0.5.0 position below** that "no migration path is provided, and
  none is planned." That stance was the absence of a policy rather than a policy. The
  contract applies **to subsequent releases only and grants nothing retroactively** —
  it does not add a migration path to 0.5.0 after the fact.
- **The pre-1.0 allowance is unchanged and deliberate.** A `public` element may still
  change incompatibly in a minor release until 1.0 is cut. What ends today is the
  silence about it, not the freedom.

## [0.5.0] — 2026-08-06

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

- **An asynchronous lifecycle** — `astart()`/`ashutdown()` mirror `start()`/`shutdown()`
  and await coroutine kind hooks and module `initialize`/`teardown`. The synchronous path
  refuses a coroutine loudly, naming it and pointing at the async path — it never skips
  or half-runs one. Stdlib `asyncio` only; `dependencies = []` holds.
- **A stated, tested concurrency contract.** Registration is atomic under one lock and
  loses nothing; racing duplicate identifiers and racing starts each have exactly one
  winner and a loud loser; reads after a completed start need no coordination. Pinned by
  `tests/test_concurrency.py`.
- **Property-based coverage of the identifier grammar and the registry invariants**
  (`tests/test_properties.py`) — universal quantification over generated names, rather than a
  fixed table of cases that only proves the examples someone thought of.
- **Declarable modes.** `[spoc.modes]` maps a mode to its cascade
  (`test = ["test", "production"]`) and merges over the default
  development → staging → production triple, so adding a mode never restates it. The
  active mode, every `[spoc.apps]` key, and every cascade entry must name a mode in the
  effective set.
- **`Registry.identifier_of(obj)`** — the canonical identifier an object is registered
  under, or `None`.
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
- **`spoc app` — adds one app to an existing project.** Same shape `init` emits, one module
  per declared kind, with the kinds read from the project's own `framework.py` rather than
  restated on the command line (`--kinds` overrides). It never overwrites an existing app and
  never edits your configuration — it prints the exact `[spoc.apps]` entry to add. `--template`
  now accepts a directory as well as an installed template set: a reference is a path exactly
  when it contains a separator (`./mytemplates`), so a bare name can never silently resolve to
  a same-named local directory.
- **Diagnostics — `spoc check`, `spoc list`, `spoc explain`.** `check` dry-boots a project and
  reports what the first real boot would raise: configuration problems, unresolvable app and
  plugin references, kind dependency cycles, identity collisions, and coroutine hooks the
  synchronous lifecycle would refuse. Findings carry the kernel's own messages, and the exit
  code is `0` clean / `1` findings. `list` enumerates registered identifiers in deterministic
  order; `explain` resolves one and describes its record. All three are library-first —
  `spoc.diagnostics` exposes `check`, `list_records`, and `explain` to code that never touches
  argv — and all three run as isolated dry boots that leave no state behind. The framework is
  found by the convention `spoc init` emits, or named with `--framework`.
- **`spoc.testing` — the test harness, shipped inside the distribution.** `ProjectTree` builds
  a project on disk from a dict of sources, `isolated()` boots one inside a scope that leaves
  no registry, import state, or loaded module behind, and `mode()` sets the mode for a block.
  A pytest plugin ships in the same distribution and surfaces the same pieces as the
  `spoc_tree`, `spoc_isolated`, and `spoc_framework` fixtures — pytest imports it, so pytest
  never becomes a runtime dependency and `dependencies = []` still holds. SPOC's own suite
  runs on the harness it ships.
- **`spoc.formats` — a data sidecar** for reading, collecting, and addressing data. Five
  formats normalize to one JSON-shaped representation, so a project stops writing a loader per
  file and per format. Addressing is split by failure semantics rather than unified: RFC 6901
  JSON Pointer resolves exactly one value or raises naming the failing segment, while RFC 9535
  JSONPath returns a possibly-empty list — configuration reads must be loud, dataset queries
  legitimately match nothing. XML repetition is declared by path rather than inferred from
  occurrence counts, so a one-element document keeps the same shape as a many-element one.
- **A reference application under `examples/`** — a storefront whose apps form one domain:
  `catalog` seeds and clears stock through module lifecycle, `orders` reaches catalog at call
  time through the registry so the only coupling between apps is the identifier grammar, and
  `auth` rounds it out. `async_main.py` is the async declaration variant. The suite boots the
  actual tree and constructs its FastAPI projection, so kernel drift against the worked example
  fails the standard gate, and the example passes its own `spoc check`.
- **`docs/architecture/kernel.md`** — the canonical Mermaid diagrams: system shape, identifier
  anatomy, resolution flow, and the kernel invariants.
- **`CONTRIBUTING.md`**, a project canon under `.canon/`, and a CI workflow that runs the
  canonical validation suite and gates releases on it.
- **`py.typed`** ships in the wheel, so downstream type checkers see the package's
  annotations, and **`spoc.__version__`** is exported from the package root.
- **`collect(ignore=(...))`** — glob patterns extending the skip set, alongside the
  hidden-entry skip that is now the default.
- **`spoc.UnmarkableObjectError`**, and **`DecodeError` / `EncodeError` /
  `MalformedAddressError`** in `spoc.formats` — the failures that previously escaped
  their family as raw `AttributeError`, `ValueError`, or a third-party exception type.

### Changed

- **BREAKING — the third identifier segment is `object_name` everywhere.**
  `Identifier.name` and the registry record's `Component.name` are both now
  `object_name`, matching the grammar (`kind:namespace.object_name`) and the error
  vocabulary. A projection reads `c.object_name`, and there is no second word for the
  same thing. `KindSpec.name`, the declaration marker's `name`, and the format codecs'
  `name` are unrelated and unchanged.
- **BREAKING — the `[spoc]` table's key set is enforced, not just documented.** An
  unknown key fails start with a `ConfigurationError` naming it and listing the valid
  set, instead of merging silently and booting the project on defaults it never asked
  for. Every offending key is reported in one run.
- **BREAKING — a re-exported marked *instance* is refused rather than silently
  re-namespaced.** When two apps' locations for the *same* kind both hold one marked
  instance, load order decided whose namespace it got. Discovery now raises
  `IdentityDivergenceError` naming both identities. Importing a registered object into
  a module of another kind (`from .models import repo` inside `views.py`) is a use,
  not a claim, and stays silent — as does re-exporting a class or function, which
  carries `__module__`.
- **BREAKING — a `[spoc.plugins]` group naming a kind that declares a metadata contract
  is refused at start**, with a message saying configured registrations cannot carry
  metadata. It previously raised a generic contract violation the author had no way to
  satisfy.
- **BREAKING — declaring the same kind twice raises** instead of the second
  declaration silently replacing the first's dependencies, optionality, and hooks.
- **BREAKING — a short CSV row is refused like an overflowing one.** Padding with
  `None` left the declared `list[dict[str, str]]` model and re-encoded as corrupted
  output. Both directions now raise `DecodeError` naming the row.
- **`collect()` skips hidden entries by default.** Any path segment starting with `.`
  is skipped before its key is derived, so a stray `.cache/x.json` can neither
  contribute entries nor fail the whole collection on a key grammar it was never going
  to use. What *is* collected stays strict.
- **`write()` creates missing parent directories** rather than failing on the directory
  above the file the caller named.
- **The missing-`spoc.toml` warning obeys `echo`**, like every other configuration
  warning — one verbosity control, not one rule per message.
- **BREAKING — apps are dotted module paths; the kernel never touches `sys.path`.**
  `[spoc.apps]` entries import through the normal import system exactly as written
  (`apps.blog`), the namespace is the path's final segment, and boot performs no
  filesystem writes — the injected `apps/` path (and the stdlib-shadowing hazard it
  carried) is gone, along with `spoc.core.paths`. Generated projects declare
  `apps.<name>` and ship `apps/__init__.py`. Restart semantics are stated honestly:
  shutdown resets what the kernel owns; Python's module cache and module-level state
  persist, so module-level code runs at most once per process.
- **BREAKING — identity divergence raises.** Re-registering an already-registered object
  under a different identity raises `IdentityDivergenceError` naming both identifiers
  instead of silently returning the prior record; same-identity re-registration stays
  idempotent. Discovery still skips objects imported from another app — an import is not
  a second declaration.
- **BREAKING — `spoc.formats` is a contained subpackage with a test-enforced boundary.**
  The data surface ships inside the one `spoc` distribution (`from spoc import formats`),
  with its codecs behind extras (`pip install "spoc[full]"`) so the bare install still
  acquires nothing. The kernel never imports it, importing `spoc` never loads it, and
  `FormatError` no longer subclasses `SpocError` — all three pinned by the suite.
- **The Python floor drops to 3.12** (was 3.13), and CI runs 3.12/3.13/3.14.
- **BREAKING — plugins register in the one flat registry.** `framework.plugins` — a second
  lookup surface keyed by dotted URI — is gone. A `[spoc.plugins]` group now names a
  *declared kind*, and each loaded reference registers as a component under the canonical
  grammar (`hooks = ["demo.extras.hook"]` → `hooks:demo.hook`), resolvable and enumerable
  like everything discovery finds. A group naming an undeclared kind fails start with
  `UnknownKindError`: configuration populates the kind set, it never widens it. A kind
  only plugins populate is declared `required=False`.
- **BREAKING — app-authored lifecycle failures propagate unwrapped.** A startup or
  shutdown hook, or a module `initialize`/`teardown`, that raises now surfaces its own
  exception with its own traceback — the blanket `SpocError("Error during
  startup/shutdown: ...")` wrapper is gone, making the documented error doctrine true.
  Kernel-authored failures are still `SpocError` subclasses, and a failed start still
  rolls back to inert.
- **BREAKING — hooks receive an ordered, immutable tuple.** Kind lifecycle hooks get
  their module's components as a `tuple` in canonical-identifier order — the registry's
  own enumeration order, identical on every start — instead of an unordered `set`.
- **BREAKING — a plugin's namespace follows discovery's grammar.** A reference reads
  `<app_path>.<module>.<attribute>` and the segment before the module is the namespace
  (a top-level module is its own), so `apps.demo.extras.hook` registers as
  `hooks:demo.hook` — previously the top-level package (`apps`) was taken. Two-segment
  references (`demo.extras.hook` → `hooks:demo.hook`) are unaffected.
- **`resolve()` succeeds in one dict hit.** The per-segment scans that make failures
  precise now run only on the failure path; grouped reads (`by_kind`, `by_namespace`)
  sort their own selection instead of re-sorting the whole store.
- **An absent collection root fails loudly.** `collect()` on a path that does not exist
  or is not a directory raises `CollectionError` naming it, instead of returning a
  silently empty mapping a typo could hide in. An existing empty directory still
  collects to an empty mapping.
- **The never-overwrite guarantee moved into the sink.** `DirectorySink.commit()` itself
  refuses a non-empty destination with `TargetNotEmptyError`; the `ProjectSink` port
  gains `location()`, so the operation no longer reaches past the port for an attribute
  it never declared.

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
- **Packaging tells the truth.** The license is MIT everywhere — `__about__.py` had
  claimed BSD-3-Clause against the repository's MIT `LICENSE` — and `pyproject.toml`
  carries the SPDX expression, PyPI description, classifiers, keywords, and project
  URLs. The sdist contains the package, its tests, and this changelog instead of the
  built docs site and process artifacts (7.4 MB → under 100 KB).
- Acronym boundaries are split correctly when deriving snake_case names.
- Hook contract and loose-mode edge cases in the core.
- `default.toml` env fallback now loads regardless of the echo setting.
- **A lifecycle call from inside a lifecycle transition no longer deadlocks.** A ready
  callback, kind hook, or module initializer calling `start()` or `shutdown()` on the
  framework currently booting it hung forever on the non-reentrant transition lock; it
  now raises `SpocError` naming the reentrant call, on both the sync and async paths.
- **A fired startup hook is always paired on a failed boot.** When a module's own
  `initialize()` raised after its kind's startup hook had run, rollback skipped that
  module and its shutdown hook never fired. The two halves are now tracked separately.
- **Configuration defaults are isolated per load.** Loaded config aliased the
  module-level default dicts and lists, so mutating `framework.config.project` corrupted
  the defaults every later `Framework` in the process would see.
- **Identity divergence no longer false-positives on shared values.** The divergence map
  is keyed by `id()`, which the runtime shares for small integers, interned strings, and
  `()` — two registrations holding equal values were reported as one object claiming two
  identities. Such values are excluded from the map; real objects still diverge loudly.
- **Malformed addresses and encoder failures stay inside `FormatError`.** An invalid
  JSON Pointer or JSONPath raised `python-jsonpath`'s own exception type, and a value the
  target format could not express raised whatever the serializer threw. `errors.py` had
  always claimed otherwise; now it is true.
- **A marked object that cannot carry the mark names the constraint.** Marking a slotted
  instance or a built-in raised a bare `AttributeError`; it now raises
  `UnmarkableObjectError` naming the object and why.
- **An unreadable `spoc.toml` is a `ConfigurationError`**, not a raw `PermissionError`
  or `OSError` escaping the kernel's error family.
- **`InvalidSegmentError` remediation matches the path taken.** A failure over a
  *derived* name told the author their explicitly-passed name was used verbatim — advice
  for a path they had not taken. It now names the intrinsic name it was derived from.
- **Template sets registered as importable packages resolve.** The entry-point group
  documented "a directory path or an importable package", but a package target was
  stringified into `Path("<module '…'>")` and reported as not found. Both the built-in
  set and entry-point sets now resolve through `importlib.resources`, so a
  non-directory installation works too.
- **Path-escape rejection covers every form the platform resolves outward.** The pure
  layer refused `/abs` and `../up` but not backslash traversal, UNC, or drive-qualified
  targets — a gap that mattered because template sets are third-party content.

### Optional extras

Installing `spoc` bare reads JSON, CSV, and TOML — all standard library.

| Extra   | Installs                          | Enables                                    |
| ------- | --------------------------------- | ------------------------------------------ |
| `yaml`  | `ruamel.yaml`                     | YAML 1.2 read/write                        |
| `xml`   | `xmltodict`                       | XML read/write                             |
| `toml`  | `tomli-w`                         | TOML **writing** (stdlib `tomllib` reads)  |
| `query` | `python-jsonpath`, `iregexp-check`| RFC 9535 JSONPath + RFC 6901 JSON Pointer  |
| `full`  | all of the above                  | everything                                 |

[0.5.0]: https://github.com/hlop3z/spoc/compare/v0.3.9...v0.5.0
