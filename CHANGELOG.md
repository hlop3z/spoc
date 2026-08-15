# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). From `1.0.0` a breaking
change to a `public` element lands only in a **major** bump; entries before it took
the pre-1.0 allowance, where a **minor** was where breaking changes landed.

What each version increment promises, and for which parts of the surface, is written
down in [Stability & Versioning](https://hlop3z.github.io/spoc/api/stability/).

## [Unreleased]

### Added

- **`CoroutineLifecycleError` — the sync-lifecycle refusal is now a type, not a
  message.** When `start()` or `shutdown()` meets a coroutine hook or module, the
  refusal used to arrive as a bare `SpocError` whose text callers had to match — which
  the stability policy explicitly says not to do. The refusal now has its own class,
  carrying `offenders` (every coroutine callable the phase would have run) and `phase`
  (`"startup"` or `"shutdown"`) as attributes. `spoc check` itself was the first
  consumer: its async-fallback retry now branches on the type instead of searching the
  message for `"use astart()"`.

  **What a consumer must do:** nothing — `except SpocError` still catches it. Code that
  matched the message text should switch to `except CoroutineLifecycleError`, which is
  the covered surface.

## [1.0.0] — 2026-08-13

### Added

- **`framework.objects` — the registry, navigated instead of spelled.** An identifier is
  `kind:namespace.object_name`. You can write it as that string, or walk those same three
  facets as attributes: `framework.objects.models.shop.product` reaches the identical
  record `framework.resolve("models:shop.product")` returns. Nothing is declared twice —
  the surface reads the registry when asked, so it cannot drift from what your apps
  registered, and a component registered later is visible to the next walk.

  **Why a second spelling exists at all: the first one does not scale.** The generated
  stub narrows `resolve` once per identifier, and past a few thousand components the type
  checkers a developer actually runs either crawl or stop answering. Measured on one file
  importing the stub: mypy takes 2.7 s at 500 identifiers, 27.5 s at 2,000, and over 300 s
  at 10,000; pyright exhausts its runtime's heap at 50,000; editor completion in pyright
  reaches 18.8 s per keystroke at 10,000, where ty stops offering completions entirely.
  The same registry described as nested members checks in 1–2 s at **50,000** components
  and completes in 0.02 s, because a member lookup is the shape every checker has
  optimized for decades.

  The practical wins beyond scale: completion arrives **per segment** — type
  `framework.objects.` and your editor offers your kinds, then that kind's namespaces,
  then its components, instead of one flat list of every identifier inside a pair of
  quotes. A wrong segment is a one-line error naming that member (mypy volunteers
  near-misses: *maybe `product`?*) rather than a wall enumerating every overload — that
  wall reaches 232 KB and 2,002 lines at 2,000 components. And the path is **always
  strict**: an undeclared member is an error in every emission mode, because it is absent
  rather than withheld, so typo detection no longer costs you `--strict`.

  `resolve()` keeps what the path cannot express: identifiers built at runtime. A kind or
  namespace named for a Python keyword takes the language's own escape — a kind `class` is
  `framework.objects.class_` — while the identifier string keeps the plain name. Failures
  are the registry's existing per-segment errors, so the same mistake gives the same answer
  by either route.

- **`spoc.FrameworkTransitioningError`** — raised when a read arrives from outside an
  in-flight lifecycle transition. Previously such a caller was told it had reentered a
  transition on its own thread, which was the wrong diagnosis with the opposite remedy: a
  racing caller may retry once the window closes, a genuinely reentrant one never can.
  Membership is now decided by context rather than thread identity, so a task that merely
  shares an event loop with a transition is told it is racing.

- **`spoc.stubs.NARROWING_LIMIT`** — the documented point (1,000 identifiers) past which
  `spoc stubs` reports that the per-identifier narrowing has outgrown the checkers, naming
  the count, the threshold, and the navigation surface. The stub is still written and the
  exit code stays `0`: a project checked only by ty is fine well beyond this, and a build
  that generates stubs should not begin failing because a project grew.

### Changed

- **The pre-1.0 allowance is spent.** Until now a `public` element could change
  incompatibly in a minor release, without a deprecation period. From this release it
  cannot: an incompatible change to a `public` element ships only in a major release,
  and only after the deprecation lifecycle has run — marked, warning at runtime,
  present through at least one full minor release, and only then removed. Nothing
  about the tiers themselves changed; what changed is that the escape hatch closed.

  The three published criteria all held before the cut, and none of them was rewritten
  to get here: every exposed element resolves to a tier, nothing intended to be
  `public` is still `provisional`, and the deprecation lifecycle has now been run
  end-to-end on a real element rather than only tested.

  `Development Status` moves from `4 - Beta` to `5 - Production/Stable` in the same
  release, because the classifier tracks the policy in force rather than a mood.

  `apidiff` changes behaviour with it. Before 1.0 it reported surface differences
  without failing — failing would have contradicted the allowance. It now fails: a
  breaking change is permitted in a major release and refused in every other, while an
  incomplete withdrawal is refused in **any** increment, because completing the
  lifecycle is what earns a removal the major release it ships in.

  **What a consumer must do:** nothing to keep working. `spoc>=1.0,<2` is now the pin
  that means something — a minor bound no longer buys extra protection, because
  minors no longer break `public` names.

- **Component metadata is supplied as `metadata=`, not `meta=`.** Registration spelled
  the concept one way and the record it populated spelled it another —
  `component(..., meta=…)` landing in `Component.metadata`, against a kind's
  `KindSpec.metadata` contract. One concept now carries one name at every surface: the
  low-level `component()` marker, every kind's registration handle, and the record. The
  old spelling is gone rather than deprecated, because it is going in the release that
  closes the allowance and nothing published depends on it yet.

  **What a consumer must do:** rename the keyword at each call site —
  `@model(meta=Meta(…))` becomes `@model(metadata=Meta(…))`. A missed site raises
  `TypeError` at import, so none can pass silently.

- **The generated stub carries the navigation surface**, in both emission modes, so
  `spoc stubs --check` reports a stored stub from before this release as stale.
  Regenerate with `spoc stubs`; nothing else changes, and the stub remains inert at
  runtime.

### Fixed

- **`spoc stubs --strict` emitted a stub that failed mypy.** The override suppression sat
  on the first overload's `def` line, but mypy anchors `[override]` on the `@overload`
  decorator above it, so every strict stub arrived with an unsuppressed error. The
  suppression now sits where mypy reads it. The pyright suppression is gone entirely —
  probing showed pyright reports nothing for this narrowing, making the comment a claim no
  checker verified. Conformance now checks *valid* code against a strict stub in all three
  checkers, which is the leg whose absence let this ship.

- **The published documentation site stopped updating.** Its workflow listened for a
  release event that a release created with the default CI token never raises, so the site
  only moved when someone dispatched it by hand and drifted several releases behind the
  code. The release now calls the docs deploy directly, after publishing.

- **`astart` / `ashutdown` refusing a busy framework is now a stated guarantee, not an
  accident of how it was written.** Both have always taken the transition lock without
  waiting, so a caller arriving during another transition is refused immediately rather
  than queued. Nothing required that: the contract asked only that a reentrant call not
  *deadlock*, which a blocking acquire also satisfies — it does eventually get the lock.
  The behavior rested on two open-coded call sites and a docstring.

  That is the wrong footing for this one, because waiting here is worse than slow. The
  transition being waited for may be running on the very event loop the waiter would park,
  in which case it could never finish and the wait would never end. Refusing is also the
  more useful answer: a caller refused for a busy framework may retry once the transition
  settles, unlike one refused for reentrancy, and it can only decide that if it is told.

  The guarantee is now written down and covered by a test that fails — rather than hangs —
  if the acquire ever starts blocking. No behavior changed; what changed is that it can no
  longer change silently.

### Removed

- **`spoc.scaffold.extract_archive`** — import it from `spoc.scaffold.archive`
  instead. The function is unchanged and unmoved; only the re-export from the package
  is gone. If you already followed the warning, nothing changes for you.

  This completes the lifecycle it was deprecated to exercise: marked and warning in
  `0.6.0`, still present and working through `0.7.0` and `0.8.0`, removed here. It was
  chosen for that in `0.6.0` precisely so the policy would have run a full withdrawal
  before it started being enforced — the other 25 withdrawals in that release took the
  pre-1.0 allowance and were removed outright.

- **`spoc.scaffold.errors.RevisionUnavailableError`** — the condition it named is
  already raised, as `RetrievalError`, by the resolver that would have raised it
  (`HttpRevisionResolver.resolve`, when the host reports no revision for a reference).
  The class was declared in `0.7.0` alongside the leaves it sat with, and never raised
  from anywhere: no code path constructed it, so no `except` clause could ever have
  caught it. Two names for one condition is the drift a single error taxonomy exists
  to prevent, and the one that was live keeps the name.

  Removed under the pre-1.0 allowance, which this release spends. After `1.0.0` a leaf
  in `spoc.scaffold.errors` — reachable, and named as importable in `0.7.0` — would
  cost a full deprecation cycle to withdraw, for a class that never fired.

## [0.8.0] — 2026-08-13

### Added

- **`spoc projection` — the registry as data, with a published schema.** The registry
  already had a machine-readable projection: it was a type stub. Any tool wanting to know
  what a project registered — a router generator, an admin surface, a docs build, a
  client in another language — had to parse a `.pyi`, turning an artifact designed for
  type checking into an interface, and its emission rules into a compatibility
  obligation. The new command writes the registry to standard output as JSON: every
  component's canonical identifier and the three facets composing it, where its object is
  defined, its shape, and the project's declared kind set. `spoc.projection.project()` is
  the same operation as a library call.

  **A JSON Schema ships with the package** (`spoc/projection/schema.json`, located at
  runtime by `spoc.projection.schema_path()`), so a consumer in any language validates
  what it received without reading Python. `kind:namespace.object_name` is the most
  durable thing this project owns — a naming standard, not a Python API — and a documented
  data projection is what makes it portable.

  Producing one is a **collect-only boot**: discovery runs, initialization does not, so a
  project whose startup hook needs a database is still describable on a machine that has
  none. The document therefore describes the registry as of the completion of discovery —
  ready callbacks are included, anything a startup hook registers afterwards is not, and
  the schema says so rather than leaving a consumer to assume completeness.

  Entries are emitted in canonical identifier order, so two projections of an unchanged
  project are byte-identical and a diff reflects the registry rather than declaration
  order, load order, or filesystem layout. The document carries `format_version`,
  independent of the SPOC release, so a file found years later still says what it is.

- **`spoc stubs` — typed registry access with no source changes.** `resolve()` returned
  `Any`, so every consumption site lost the type it had just looked up and a mistyped
  identifier failed at runtime instead of in the editor. The new command dry-boots a
  project and writes a type stub beside its composition root: `resolve()` now yields the
  real type of each component, and editors complete both the identifier string and the
  object. Existing call sites are untouched — the stub is the whole change. `--check`
  verifies a committed stub without writing it (a missing stub is a mismatch, not a
  pass), and `--strict` drops the catch-all overload so a misspelled identifier becomes a
  type error, at the cost of requiring literal identifiers.

  A **stub** rather than a generated module, deliberately: a `.pyi` never executes, so it
  can name another app's classes for the type checker while the apps stay exactly as
  decoupled at runtime as before. Deleting it changes no behaviour.

  Types that cannot be determined faithfully degrade to `Any` and are counted rather than
  guessed at, and the command reports how many.

- **`Framework.resolve_type` and `Framework.resolve_object`** — typed access without
  generating anything. Each takes a caller-owned contract (typically a `Protocol` the
  *calling* app declares), so a consumer can type what it resolves without importing the
  module that provides it. Shape — constructible, value, or callable — is checked at
  access time and raises the new `ComponentShapeError`; structure is deliberately left to
  the type checker rather than re-verified at runtime.

- **`spoc.KindHandle`** is now exported, and `Framework.kind()` returns it instead of an
  untyped callable. Registration is identity, so the handle is typed to return exactly
  what it was given — meaning `@model class Product` no longer erases `Product` to `Any`
  at its declaration site.

- **A three-checker conformance gate** (`tests/test_conformance.py`). mypy, pyright, and
  ty each read one generated stub and must agree. `ty` alone could not hold this
  contract: it is beta at 0.0.x and runs in no user's editor, so a stub could pass CI and
  still fail everyone. pyright is the engine behind Pylance, which makes it the authority
  on the claim that VS Code completion works.

### Changed

- **The four command mount points are now `provisional` rather than internal.**
  `spoc.scaffold.register`, `spoc.diagnostics.register`, `spoc.projection.register`, and
  `spoc.stubs.register` mount SPOC's commands onto a parser you own, which is how a
  framework built on SPOC publishes them under its own name — `hello init`, `hello check`.
  Each was reachable only through a submodule, which made it internal, while
  `ENTRY_POINT_GROUP` and `template-set:default` were already public: a framework author
  was promised where templates come from and told nothing about how the commands using
  them are reached. All four are now exported from their packages and carry the
  provisional notice.

  Not `public`: the signature takes `argparse`'s own private subparser type, and promising
  that in perpetuity would commit every downstream framework to `argparse` as firmly as it
  commits SPOC. What is promised is which commands each mount contributes and what invoking
  them does. Each notice names what would settle the tier — a framework outside SPOC
  actually mounting it, or SPOC committing to a parser choice.

  `spoc`'s own CLI now reaches all four by the published path, so the shipped program is a
  consumer of the extension point rather than a privileged assembly of it. Mounting a
  command also no longer loads the machinery behind it.

- **A lifecycle phase is linear in the project's own size.** Hook dispatch asked the
  registry for a module's components once per loaded module, and each ask snapshotted and
  sorted the whole store — M modules over N components meant M full scans, so startup and
  shutdown were quadratic in how much the project itself declared. The registry is now
  grouped once per phase, built on first use so a project with no hooks pays nothing. At
  400 modules over 50k components a phase went from 4.2s to 17ms. Every hook in a phase
  now also reads one observation of the registry rather than M separately built ones.

  Two smaller costs went with it: the load order was re-derived once for the
  coroutine-refusal scan and again for the dispatch that scan guards, and `_kind_ranks`
  called `list.index()` inside a sort key.

- **`resolve()` is 7.9x faster and flat to 20k components.** It was spending 81% of its
  time re-deriving a value from a string that had already passed the grammar — 1870ns of
  2340ns, against a 33ns dict hit. Identifier parsing is now memoized, bounded exactly as
  `to_snake_case` already was, so an application resolving identifiers built from user
  input cannot grow the cache without limit. Malformed identifiers are not memoized and are
  reported exactly as before. 2340ns → 295ns.

- **One registry now has one description.** `spoc.diagnostics.RecordInfo` is gone,
  replaced by `spoc.projection.ComponentEntry`; `list_records` and `explain` return the
  latter, still after a full boot. Two private structures described the same components
  with four fields in common and neither able to leave the process — and they had already
  drifted: `RecordInfo` located an object by its `repr` when it carried no `__qualname__`,
  which for a registered *instance* embeds a memory address. Untidy in prose output; in a
  document meant to be diffed it would have made two projections of one unchanged registry
  differ. Components are now located by their type in that case, in the one place the rule
  lives. `spoc explain` also reports `shape` now.

- **BREAKING: the shape vocabulary is `constructible` / `callable` / `value` everywhere.**
  `spoc.stubs.Shape` spelled the first one `"class"` while typed access's errors said
  "a constructible object", and the two classifiers were separate implementations of one
  rule. There is now a single classifier (`spoc.core.shape`), and the projection publishes
  its tokens — `constructible` says what a consumer may *do* with an object, where
  `"class"` named a Python spelling and would mean nothing to a reader in another
  language. No stub output changes; the token is not emitted into a `.pyi`.

- **The load order is now a stated guarantee rather than an emergent one.** A kind is a
  phase, and a phase spans every app: every app's `models` modules load, discover, and
  initialize before any app's `views` modules, so a `views` startup hook always sees a
  fully registered world. Within a phase, the effective `[spoc.apps]` order decides, and
  shutdown reverses the whole order exactly. **Nothing moves for a project whose apps
  each declare each kind** — this was already the behaviour, but it came from
  `graphlib`'s batching, which documents no order among modules of one phase. The order
  is now computed from the declaration and pinned by tests; `graphlib` is kept for
  refusing a dependency cycle. The one knob this exposes is documented under
  [Apps](https://hlop3z.github.io/spoc/learn/apps/).

- **BREAKING: two apps can no longer share a namespace.** A namespace derives from an app
  path's final segment, so `apps.shop` and `vendor.shop` both answered to `shop` — and
  merged silently unless they also happened to declare the same object name, at which
  point the resulting duplicate-identifier error named a third place entirely. Nesting
  apps under a container package is what every project does past a handful of apps, which
  is exactly what makes the clash likely. Start now fails naming the contested namespace
  and both packages, before anything is imported.

  Settle it with an `as` clause rather than by renaming a package you may not own:

  ```toml
  [spoc.apps]
  development = ["apps.shop", "vendor.shop as vendor_shop"]
  ```

  A `[spoc.plugins]` reference follows the same rule — and inside an aliased app it
  follows the alias, because the package owns the name. Registering into your own app's
  namespace from a plugin group is unaffected; so is a plugin reference into a package
  that is not an installed app at all.

- **`Component` is now generic** (`Component[T]`, with `object: T`). Written bare,
  `Component` places no constraint on `object` and means exactly what it meant before, so
  no existing annotation or call site changes meaning; the parameter exists for readers
  that know more — a generated stub narrows it per identifier, a typed accessor per call.

- **Framework location moved from `spoc.diagnostics.locate` to `spoc.locate`.** Locating a
  project's composition root is shared tooling, needed by both the diagnostics and the
  stub generator, and only `spoc.cli` may import the diagnostics. `spoc.diagnostics` still
  re-exports `DEFAULT_FRAMEWORK_REF` and `LocateError`, so its public surface is unchanged.

- **SPOC is described as a component registry, not a kernel.** The package
  description, the README, the documentation home, and the architecture title all
  claimed a "registry-first runtime kernel". Nothing in SPOC schedules, isolates, or
  mediates; after `start()` returns it does nothing for the life of the process, and
  an app can bypass the registry entirely by importing another app directly — a
  system you can route around is not a kernel. The accurate classification is a
  component registry with a total naming grammar and a dependency-ordered lifecycle,
  and the positioning line is the one the docs already used: *SPOC helps you build
  your own framework.* **Documentation only** — no code, no API, and no behaviour
  changed. The word survives in `docs/architecture/kernel.md` and in source
  docstrings as shorthand for the core package as against the contained subpackages
  (`spoc.formats`, `spoc.testing`, `spoc.diagnostics`, `spoc.scaffold`); that
  document now states the narrower meaning outright so it cannot drift back into a
  claim.

- **The declared platforms are now Linux, Windows, and macOS**, replacing
  `Operating System :: OS Independent`. That classifier was a claim no gate can
  satisfy — CI ran on Linux alone while development happened on Windows — and the
  project now states the set it actually verifies. The validation suite runs on all
  three, across every supported Python version, and the platform scope is recorded
  in `.canon/checks.md`, which CI and `task check` both derive from. Nothing about
  where SPOC *runs* changed: it remains pure Python with no dependencies. What
  changed is which platforms it is prepared to answer for. A green local run is now
  correctly described as evidence for one platform rather than for the pipeline.

### Fixed

- **The concurrency contract claimed more than it covers.** It said reads after a completed
  start need no coordination. Reads racing *shutdown* are not covered: reset swaps in a
  fresh registry rather than emptying the live one, so such a read observes one whole
  registry — never a torn state — but which of the two it observes is a race, and the empty
  one reports the same unknown-segment failure any absent component would. A caller that
  resolves concurrently with shutdown must order the two itself. Documentation only; the
  behavior is unchanged and was always this.

- **An app omitting an optional module pulled its remaining modules a phase early.** With
  kinds `models → views → urls` where `views` is optional, an app without a `views.py`
  had its `urls.py` initialize one phase too soon — ahead of another app's `views.py`,
  breaking the phase guarantee, and ahead of an earlier-listed app's `urls.py`, breaking
  the app order. The absent module was skipped before it reached the dependency graph,
  but the module depending on it put the name straight back as a node with nothing
  before it, which made everything downstream of the gap look shallower than it is. Kind
  order now comes from the declaration, where a module that does not exist has no say.
  This is the only case whose order changes; a project where each app declares each kind
  boots in exactly the order it did.

- **A cycle among declared kinds went unnoticed when no app provided both modules.**
  `KindSpec("a", depends_on=("b",))` with `KindSpec("b", depends_on=("a",))` was only
  caught through the modules the apps happened to have, so a cycle between two optional
  kinds nobody had files for started cleanly. It is now refused at start, naming the
  cycle, with the same `CircularDependencyError`.

- **A revision could be served another revision's cached template set.** Retained
  content is keyed by the exact revision it was retrieved for, but the key was built
  by filtering the revision down to path-safe characters — a lossy step, so
  `feature/x` and `featurex` both addressed one entry, as did every revision that
  filtered away to nothing. The mapping is now total: a revision already usable as a
  path segment is used verbatim, and anything else is named by its digest, so
  distinct revisions keep distinct entries. An empty revision is refused outright,
  naming the reference the caller supplied. **No revision reachable through the
  reference grammar could trigger this** — a revision containing a separator is not
  parsed as a revision at all — so it was reachable only from a host reporting an
  unusual commit id, and nothing currently cached is invalidated by the new mapping.

- **Losing a race to cache a revision leaked a staging directory.** When two
  processes retrieved the same revision at once, the one that finished second
  correctly used the copy that landed first — and left its own staged copy behind in
  the cache root. Nothing expires from that cache by design, so every lost race cost
  a directory permanently. The staged copy is now removed on that path.

- **A kind named for a Python keyword no longer generates a project that fails to
  parse.** `spoc init shop --kinds class` emitted `class = framework.kind("class")`
  and `from framework import class` — two `SyntaxError`s. The kind was never the
  problem: the identity grammar accepts `class` and the kernel registers it, so only
  the generated variable needed spelling around the language. It now carries PEP 8's
  trailing underscore (`class_`), the escape applies to a singular that lands on a
  keyword too (`--kinds ifs` now gives `if_` where it previously fell back to `ifs`),
  and derived names are checked for collisions *after* escaping, so no two kinds can
  bind the same variable. **Affects newly generated projects only.**

## [0.7.0] — 2026-08-11

### Changed

- **Generated decorators are named in the singular.** `spoc init` now emits
  `model = framework.kind("models")` and app modules that import `model`, where both
  previously echoed the kind name. A kind names a category (plural); the decorator
  marks one member of it, so `@view` reads correctly on the function it sits above.
  The name is derived conservatively — only unambiguous cases change, and a singular
  form that would collide with another kind or shade a Python keyword falls back to
  the kind's own name, so a generated project always imports. Both built-in template
  sets, the storefront example, and the documentation now agree; previously the
  example and the templates disagreed. **Affects newly generated projects only** —
  nothing in the installed package changed, and an existing project is untouched.

### Added

- **Documentation that cannot drift** (docs only — no package change). Every Python
  fence in the docs now runs in CI or carries an explicit skip marker, with printed
  output verified against `#> ` comments; ten pages are executed as complete
  projects, file for file, the way a reader would run them. The API reference
  derives its member lists from `__all__`, the CLI page captures the real
  `--help` at build time, and a strict docs build joins the validation gate. New
  pages: **Build a Framework** (an end-to-end tutorial — empty folder to a
  `curl`-able HTTP framework in four files, executed by the test suite), a
  task-oriented **How-To** section (database resource, transport binding,
  settings validation, testing, shipping a reusable app — all executed), and an
  **Error Index** mapping every public exception to its trigger and fix, held
  complete by a test.
- **The `starter` template set** (provisional). `spoc init myproject --template starter`
  generates a *running application*, not just a bootable skeleton: the five-kind
  default vocabulary (`models`, `views`, `commands`, `resources`, `hooks`) wired end
  to end, a transport-neutral projection module (`surface.py`), and a working project
  CLI (`python main.py <namespace.command>`) — with zero dependencies beyond SPOC.
  The starter chooses no transport; binding the projection to HTTP, messaging, or a
  worker loop is a few documented lines in the generated project. Fully concrete on
  purpose (`--kinds` does not apply): the `resources` kind's lifecycle wiring cannot
  be expressed by name substitution.
- **A default kind vocabulary.** The five kinds above are now documented as SPOC's
  conventional vocabulary — the names reusable apps may assume — with the resource
  lifecycle recipe (an instance component the kind's `on_startup` opens, `resolve`
  reaches, and `on_shutdown` closes). Convention only: deviation stays fully
  supported, and the kernel is unchanged. The storefront example now demonstrates
  the recipe (`resources:catalog.search_index`, resolved mid-call by
  `views:catalog.find_product`).
- **App-owned configuration tables.** `spoc.toml` tables outside `[spoc]` were
  parsed and silently discarded; they now reach the application, as parsed, on
  `framework.config.tables`. The kernel claims exactly one top-level table — stated
  as a contract, so an app table can never collide with a kernel one — and validates
  nothing outside it; the docs show the seam with a plain pydantic model as the
  worked example. The `[spoc]` closed key set is unchanged.

## [0.6.0] — 2026-08-10

### Added

- **A stability contract.** Every element of the published surface — importable names,
  the `spoc` command, the pytest plugin and its fixtures, the extras, the `spoc.toml`
  schema, and the template set format — now carries exactly one tier: `public`,
  `provisional`, or `internal`. For an importable name the tier follows from the source:
  exported from a package is `public`, saying "may change incompatibly in a minor
  release" in its own docstring makes it `provisional`, and a name reachable only through
  a submodule is `internal`. Everything that is not an import — the command, the entry
  point, the extras, the fixtures, the schema, the template set — is listed in
  `[tool.spoc.stability]` in `pyproject.toml`, because nothing can read a tier off it.
- **`spoc.component`.** The low-level marker was only reachable as
  `spoc.core.declaration.component`, which the docs told you to import even though
  `spoc.core` is internal. It is now re-exported at the top level. The old path still
  works but is internal and carries no promise — use `from spoc import component`.
- **`apicheck`**, a workshop tool (`cd scripts/py && uv run apicheck ../..`) that fails
  when an exposed element resolves to no tier, when the manifest declares something the
  surface no longer exposes, or when it declares something the surface never exposed. It
  runs in the same gate as the tests.
- **`apidiff`**, its companion (`cd scripts/py && uv run apidiff ../..`), which compares
  the working tree against the last release tag and reports every element added, removed,
  or moved between tiers, plus every incompatible change. Until 1.0 it reports without
  failing, because the pre-1.0 allowance permits those changes; from 1.0 it fails. From
  1.0 the increment is also weighed: an incompatible change is what a major release is
  for, so breakages are permitted there and refused in every other increment. Without
  that, the first release able to remove a deprecated element could never pass its own
  gate.
- **A deprecation signal** following PEP 702 — `warnings.deprecated` on 3.13+, with a
  stdlib-only fallback on 3.12. `dependencies` stays empty.
- **The deprecation lifecycle is now enforced by the same comparison that checks
  compatibility**, rather than resting on a reviewer remembering that an element existed.
  `apicheck` reads each element's withdrawal mark out of the source and fails when a
  notice names no replacement and does not say there is none, or when a
  `DeprecationWarning` is raised outside `spoc.core.deprecation` — withdrawal has exactly
  one spelling, because the absence of a mark can only mean "not being withdrawn" if
  there is one way to write one. `apidiff` establishes, for every removed element, which
  release first marked it, by walking the published releases behind the removal. The wait
  is counted in **minor lines, not tags**: `0.6.1` shipping after `0.6.0` marked something
  is one release, not two. A history it cannot establish is reported `undetermined` and
  exits non-zero — never read as a completed lifecycle.

  Withdrawal is tracked **beside** the tier, never as a tier of its own: a marked element
  keeps every promise its tier makes until the release that removes it, which is the
  entire point of the waiting period.

### Changed

- **`spoc.scaffold` publishes 24 names instead of 49.** Every name the package exposed
  has had its intended tier for 1.0 decided, against a stated rule rather than by taste:
  a name is re-exported only if a consumer outside the package must write it to invoke an
  operation, implement a contract the package accepts, distinguish a condition they can
  respond to differently, or supply a value the package reads. The withdrawn names are
  listed under **Removed** below; each remains importable from the module that defines
  it, and promises nothing there.
- **`UnrecognizedReferenceError` and `RetrievalError` are now `public`.** Both dropped
  their provisional notice: a caller can act on each differently — correct a reference's
  spelling, or fall back to a local template set — which is what earns a promise.
- **A `provisional` element must now say what would settle it.** The notice alone marked
  a tier without recording whether it was a decision or an omission. Four elements remain
  `provisional` past 1.0, each stating its open question: `Origin`, `RECORD_NAME`, and
  `read_origin` settle when the project decides whether a generated project's origin
  record must also carry the substitution values a generation used; `EnumerableSource`
  settles when a template source outside the package implements it. `apicheck` fails on a
  notice that only hedges.
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

### Deprecated

- **`spoc.scaffold.extract_archive`** — import it from `spoc.scaffold.archive` instead.
  The re-export warns today and is removed at 1.0; the function itself is not going
  anywhere, and reaching it through its own module is silent. Archive admission is how
  retrieval is made safe rather than something a consumer composes with, so it belongs to
  the module that performs it.

  This is the element the deprecation lifecycle is being exercised on. The other 25
  withdrawals took the pre-1.0 allowance and were removed outright; this one runs the
  full course, because a policy that requires a lifecycle should have run one before it
  starts being enforced.

### Removed

- **25 names are no longer exported from `spoc.scaffold`.** Every one is still importable
  from the module that defines it — what changed is what is promised, not what is
  reachable.

  Five of them were in the surface `0.5.0` published and are genuine removals:
  `PathConflictError`, `PathEscapeError`, `IncompleteTemplateSetError`,
  `UnsatisfiedValueError`, `UndeclaredValueError`. The other twenty were exported by work
  that has not been released yet and are withdrawn before they ever ship — listed here
  because the export list is what a reader will diff, not because anything depended on
  them. Grouped by why:

  - *The retrieval ports, and the vocabulary they speak* — `Reference`, `ReferenceKind`,
    `RevisionResolver`, `Fetcher`, `Cache`. None appears in the signature of a public
    operation; they exist to construct `RemoteTemplateSource`. Now in
    `spoc.scaffold.plan`.
  - *The retrieval adapters* — `HttpRevisionResolver`, `HttpFetcher` (now in
    `spoc.scaffold.remote`), `DirectoryCache`, `default_cache_root` (now in
    `spoc.scaffold.cache`), `RemoteTemplateSource` (now in `spoc.scaffold.sources`).
  - *Archive admission bounds* — `MAX_EXPANDED_BYTES`, `MAX_MEMBERS`. Now in
    `spoc.scaffold.archive`.
  - *The record-writing half of provenance* — `record_content`, `record_file`,
    `describe_divergence`. Reading a project's origin stays public; writing the record is
    the generating operation's own business, and `AddedApp.divergence` already carries
    the only comparison result a caller needs. Now in `spoc.scaffold.provenance`.
  - *Ten error leaves whose only distinct response is different wording* —
    `PathConflictError`, `PathEscapeError`, `IncompleteTemplateSetError`,
    `UnsatisfiedValueError`, `UndeclaredValueError`, `ReservedTargetError`,
    `InsecureRedirectError`, `MemberRefusedError`, `BoundExceededError`,
    `RevisionUnavailableError`. Catch `ScaffoldError` for the category, or import the
    leaf from `spoc.scaffold.errors`.

  Permitted by the pre-1.0 allowance, which is spent at 1.0 — after which the same
  withdrawal would cost a full deprecation cycle. That is why it happened now.

- **`TemplateSource.available()`** — the protocol was split, and enumeration now lives on
  `EnumerableSource`, because a remote resolver cannot answer "what template sets exist".
  A template source that only loads by name satisfies `TemplateSource`; one that can also
  list itself satisfies `EnumerableSource`. `TemplateSource` is `public` — it is a
  parameter of `init_project`, so a caller cannot avoid naming it. `EnumerableSource` is
  `provisional` until something outside this package implements it.

  This is recorded late. The change shipped with the remote-template work and no gate
  could see it at the time; `apidiff` found it on its first run against `v0.5.0`. The
  pre-1.0 allowance permitted the removal, so nothing is being reverted — but the
  contract requires every surface change to be recorded, and this one was not.

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

[1.0.0]: https://github.com/hlop3z/spoc/compare/v0.8.0...v1.0.0
[0.8.0]: https://github.com/hlop3z/spoc/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/hlop3z/spoc/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/hlop3z/spoc/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/hlop3z/spoc/compare/v0.3.9...v0.5.0
