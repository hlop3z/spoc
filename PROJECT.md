# SPOC — Consolidated Reference

> The standing project overview: the architecture in force and the behavior contracts
> (Capabilities) the test suite pins. The engineering rules live in `.canon/`;
> full-length decision records live in `DECISIONS.md`. When this file and the code
> disagree, that is a defect in whichever is wrong — fixed in the same change set.

SPOC is a zero-dependency Python kernel for building frameworks: a registry-first core
where every managed object has one canonical identity, and every surface (CLI, stubs,
projections, docs) is derived from that single registry.

## Architecture

- **One published distribution (`spoc`), zero runtime dependencies.** `dependencies = []`
  is an enforced, load-bearing invariant — the single most frequently decisive constraint
  in every design decision. Optional capability dependencies live behind extras (`yaml`,
  `xml`, `toml`, `query`, `full`); dev tooling lives in dependency groups and never
  reaches an installer. A standing owner mandate: exactly one PyPI distribution, never
  re-split.
- **Kernel plus contained subpackages.** `src/spoc/` = `framework.py` + `core/`; beside it
  `formats/`, `scaffold/`, `testing/`, `diagnostics/`, `stubs/`, `projection/`. The kernel
  imports none of them, each is deletable without touching the kernel, and the boundary is
  pinned by tests (importing `spoc` must never load `spoc.formats`; `FormatError` must
  never subclass `SpocError`).
- **Pure core, adapters at the edge, dependencies inward only.** Core modules (`identity`,
  `registry`, `declaration`, `exceptions`, `transition`) do no I/O and import nothing
  outside the kernel. Adapters: `loader` (Python import system), `config` (filesystem +
  TOML). The same shape repeats inside every subpackage: a pure `core.py`/`plan.py` naming
  ports, adapters implementing them, and a `cli.py` that parses and renders only.
- **Composition wiring has exactly two homes.** `Framework` is the runtime composition
  root and the only place kernel adapters are wired; `spoc/cli.py` is the tooling
  composition root, mounting each subpackage's `register` and injecting cross-subpackage
  collaborators (`derive_kinds`, `source_factory`, retrieval ports). No subpackage imports
  another.
- **Registry-first kernel.** One store of `Component` records; every grouped view is
  derived, never maintained as independent state. The store is keyed by the grammar's own
  segments (kind → namespace → object name), so a facet is a sub-dictionary and drift
  between store and index is structurally unrepresentable.
- **One canonical identity, defined in one place.** `kind:namespace.object_name`, each
  segment `^[a-z][a-z0-9_]*$`, exactly three segments. Validate-never-normalize, with one
  deliberate carve-out: values the kernel derives from `__name__` are converted then
  validated; values a human states are verbatim or rejected. Resolution never converts.
- **Layout is taxonomy.** `<app>/<kind>.py`; an app is a dotted module path imported as
  written (no `sys.path` mutation); the path's final segment is the namespace, uniquely
  owned via an ownership map built before any import, with `"pkg.path as alias"` as the
  escape hatch.
- **Kinds are a closed set fixed at construction**, each one `KindSpec(name, depends_on,
required, metadata, on_startup, on_shutdown)` — one record, not parallel dicts keyed by
  kind name.
- **Describes, never executes.** Resolution returns the object uninvoked; the kernel calls
  user code only through declared lifecycle hooks. This invariant rules out DI containers
  and service locators at the registry layer.
- **Two-phase lifecycle, mirrored sync/async.** `__init__` declares and is inert;
  `start(base_dir)` / `astart()` does all work in a fixed order (config → apps → plugins →
  discovery → `on_ready` → module init). Only hook dispatch and module init/teardown fork
  between the sync and async paths; everything else is shared and synchronous.
- **Transition arbitration is one unit.** `core/transition.py`'s `TransitionGate` owns all
  three pieces of state: a `threading.Lock` entered blocking (sync) or non-blocking
  (async), and a `ContextVar` marking membership. Membership answers both reentrancy
  refusal and racing-read refusal; work spawned by a transition inherits the exemption,
  unrelated callers do not.
- **Errors are the contract.** A typed `SpocError` family; resolution fails per segment in
  order kind → namespace → object_name, naming the value and the valid candidates; no
  `None` returns on any lookup path; app-authored exceptions propagate unwrapped with
  their original type and traceback.
- **Load order is owned, and separate from enumeration order.** Modules sort by an
  explicit `(kind_depth, app_index)` key producing a cross-app phase barrier with an
  app-list tiebreak; `graphlib` is retained only for cycle detection. Enumeration
  (`by_kind`, `all`, hook payloads, projections, stubs) is always canonical-identifier
  order, so unrelated changes never churn a committed artifact.
- **Configuration is one file, closed at the edges.** `config/spoc.toml` (or `spoc.toml`);
  `[spoc]` is a closed key set rejecting unknowns loudly; every other top-level table
  passes through to the application untouched. No `settings.py` is ever read. The mode
  cascade merges over a default triple (development → staging → production).
- **The public surface is derived from the artifact, not declared.** Exposure from a
  package `__init__` ⇒ `public`; a provisional notice in the docstring ⇒ `provisional`
  (and it must state its settling condition); submodule-only ⇒ `internal`. Only non-import
  elements (console script, entry points, extras, fixtures, schema, template set) remain
  declared in `[tool.spoc.stability]`. Deprecation is a withdrawal field beside the tier,
  never a fourth tier.
- **Surface governance lives outside the package.** `apicheck` (contract assertion) and
  `apidiff` (cross-release delta + withdrawal lifecycle) are development-time tools in
  `scripts/py/tools/`, built on griffe, and they never import `spoc` — a checker that
  imports its subject audits whatever happens to be installed.
- **Data is not code.** Template sets are directories of native-format files behind a
  `TemplateSource` port; the projection's JSON Schema is a checked-in file; the origin
  record is a data structure handed to a serializer. No format is assembled in program
  code, and no template content is executed.
- **The scaffolder computes a plan, then commits it.** A pure core resolves templates,
  validates names, and returns an immutable ordered `(path, content)` plan; an adapter
  stages to a temp directory and commits atomically. "Nothing is written on failure" is
  therefore structural. Ports: `TemplateSource`/`EnumerableSource` and `ProjectSink`
  (public — they appear in a public operation's signature); `Fetcher`,
  `RevisionResolver`, `Cache` (internal — they only build an adapter).
- **The registry has one description and several projections.** `spoc list` (full boot,
  human-readable), `spoc projection` (collect-only boot, JSON against a published
  schema), `spoc stubs` (`.pyi` over the project's composition root, plus a nested
  navigation tree). One data layer; only rendering and boot depth distinguish the
  commands.
- **Integrity is mechanical, and gates have one home.** The examples tree and the
  docs/README pages are the fixtures — executed, not mirrored — so drift becomes a failing
  test rather than a broken downstream project. `.canon/checks.md` is one row per command;
  both `Taskfile.yml` and CI derive from it, so `task check` and CI are the same gate
  across the declared platform matrix (Linux/Windows/macOS × three Pythons).

## Capabilities

Each entry is the capability's purpose and the invariants that must hold, condensed;
the test suite is what pins them.

### Kernel

#### object-identity

- **Purpose:** Give every managed object exactly one canonical identifier,
  `kind:namespace.object_name`, validated at registration and never inferred from the
  execution environment.
- **Must hold:**
  - Each segment is non-empty and matches `^[a-z][a-z0-9_]*$`; no other identifier form
    exists. Wherever segments are exposed individually, the third is named `object_name` —
    one vocabulary across grammar, record fields, and errors. Round-trip parse/compose
    holds over the whole grammar; rejection is complete over the whole input space (never
    accepted, converted, or partially parsed).
  - An explicitly stated segment is used verbatim and validated, failing with an error
    naming the offending segment and value — never silently transformed. A derived name
    (from the object's intrinsic name) is converted to canonical snake_case then validated
    identically. Failure messages describe the path actually taken (stated vs derived).
  - Lookup stays exact: resolving never converts the string, so a non-canonical spelling
    of a registered identifier fails to resolve.
  - The kind set is declared explicitly in composition configuration before any
    registration; an unknown kind fails naming it and listing the declared kinds; no API
    extends the kind set at runtime.
  - An object with no intrinsic name must be registered with an explicit name; identity is
    never inferred from the execution environment (caller variable names, stack
    inspection), and the object is never mutated to derive identity.
  - A namespace belongs to exactly one package for a running project's lifetime; two
    packages resolving to one namespace are refused (not merged), naming the contested
    namespace and both claiming packages, decided before any component of that namespace
    registers.

#### component-registry

- **Purpose:** One flat, enumerable store of component records as the kernel's single
  source of truth, from which every projection is derived.
- **Must hold:**
  - All components live in one enumerable collection; kind, namespace, and name are
    queryable facets of it, never separate stores; grouped views are derived. Any
    non-derivable state is written in the same atomic step that admits a registration. A
    partially admitted registration is never observable in any view.
  - Registration is loud: a declared component that cannot be registered fails startup
    naming the object, its declared location, and the reason — never silently dropped.
    Duplicate canonical identifiers fail naming the identifier and the already-registered
    object.
  - Each record exposes at minimum the canonical identifier, the three segments
    individually, the registered object, and metadata conforming to its kind's stated
    contract, plus optionally a type description. External consumers can build projections
    from records alone without importing kernel internals. A record carries no second
    free-form configuration channel beside its metadata.
  - One object, one identity: re-registering an object under its existing identity
    succeeds idempotently; under a different identity it fails naming both identifiers.
    Equal immutable values sharing one runtime object (interning) registered under
    different identifiers both succeed.
  - Discovery loudness applies only where a second claim is made: an object appearing in a
    location declaring a different kind is skipped silently (it was imported for use); two
    locations of the same kind deriving different identities for one object fail start
    naming both — load order never decides.
  - Registrations are atomic under concurrency: none lost, duplicate/divergence guarantees
    hold under any interleaving, enumeration and resolution never observe a partial
    record. A failed resolution describes one consistent observation, without holding
    exclusive access across app-authored code. Invariants hold for arbitrary generated
    operation sequences, not only named examples.
  - Enumeration yields each matching record exactly once in deterministic order. Reading
    one facet costs in proportion to that facet, not the whole registry. Ordering
    derivation is paid at most once per change to the registered set, not once per read.

#### component-resolution

- **Purpose:** Turn a canonical identifier into its registry record — a pure lookup whose
  failures name the exact segment that did not resolve.
- **Must hold:**
  - Resolution proceeds segment by segment in the fixed order kind → namespace →
    object_name.
  - A failed resolution raises (never returns an empty result) with an error naming the
    failing segment, its value, and the valid candidates at that step; a malformed
    identifier names the expected grammar and the received value.
  - A segment failure means the segment: when resolution cannot be served because the
    framework is transitioning, the failure is reported as that condition with a distinct
    error type, naming no segment as unknown — the two conditions have opposite remedies.
  - Resolution is a pure lookup: it never calls, constructs, or executes the resolved
    object.
  - The grammar accepts no operation suffix; a fourth segment (e.g. `model:blog.post.create`)
    is rejected as malformed.

#### framework-declaration

- **Purpose:** Declare a framework exactly once on one object — its closed kind set,
  inter-kind dependency order, per-kind attributes, and registration handles.
- **Must hold:**
  - Exactly one object carries the closed kind set and everything the kernel knows per
    kind (dependency position, required/optional, metadata contract). Declaring the same
    kind twice fails naming it; a later declaration never silently replaces an earlier
    one.
  - The inter-kind dependency order holds project-wide, not per app: the depended-on kind
    completes across every installed app before the dependent kind begins anywhere.
  - Every kind states whether its modules are required or optional, per kind and never
    framework-wide; unstated defaults to required, so tolerating a missing module is
    always deliberate.
  - A kind may state a component metadata contract; a violation fails naming the kind, the
    component, and the departure. A kind stating no contract means its components carry no
    metadata — there is no untyped channel by default. Every surface accepting it calls it
    `metadata`.
  - The framework object hands out a registration handle for any declared kind; requesting
    an undeclared kind fails immediately naming the unknown kind and the declared set.
    Marking an object that cannot carry the mark fails with a kernel error, never a raw
    attribute error.
  - Handles are directly usable in bare form (name derived) and named form (explicit
    conforming name), with no wrapper code. Handles are obtainable from an unstarted
    framework so app modules can mark objects at load time; marks are collected during
    discovery.
  - A kind's startup and shutdown hooks are declarable as plain functions or coroutine
    functions on the same declaration attribute.

#### framework-lifecycle

- **Purpose:** An explicit phase contract — inert construction, loud discovery on explicit
  start, a single post-discovery ready phase, and ordered shutdown — with nothing
  happening as a side effect of import.
- **Must hold:**
  - Construction has no observable side effects; it only records the declaration. All
    discovery happens in one explicit `start` taking the project root; starting an
    already-started framework fails rather than silently re-discovering.
  - A missing module for a kind is decided by that kind's own optionality alone: required
    → start fails naming app, kind, and expected module; optional → skipped silently. A
    module that exists but raises on load is always an error.
  - A ready phase fires callbacks registered before start exactly once, after all
    components are registered and before start returns, in registration order, with read
    access to the completed registry; a ready callback failure fails start.
  - Load order is a stated total order with exactly two keys in precedence: kind depth in
    the declared inter-kind dependency order, then the module's app position. Kind depth
    is read from the declaration, never from which modules were found. The order is stable
    across starts, independent of filesystem layout or import order, and is the
    framework's own property. A cycle in the declared kind order fails start naming the
    cycle.
  - Kind startup hooks and module initialization fire in load order, with paired shutdown
    work in exact reverse; a dependent kind's startup hook never runs before the
    depended-on kind's has run for every installed app.
  - Hooks receive their app's components of that kind as an immutable collection in
    canonical identifier order. Hook dispatch is per loaded module; configured
    registrations without a backing app module do not by themselves fire hooks (stated in
    the lifecycle documentation).
  - Boot acquires no process-global state: no module-search-path mutation, no filesystem
    writes, no package made importable under a new name; the only residue is the runtime's
    ordinary module cache.
  - Lifecycle transitions are serialized against each other and themselves: exactly one
    racing start proceeds; a shutdown racing a start observes fully-started or
    fully-inert, never a partial boot. A transition invoked from inside an in-flight
    transition fails immediately naming the reentrant call and never deadlocks.
    Inside-vs-outside is one determination — whether the transition invoked the caller
    (directly or through spawned work) — applied identically to reads and transitions on
    both sync and async paths. A concurrent outside caller gets _transition already in
    progress_, distinct from reentrancy: their remedies are opposite.
  - A resolution from outside an in-flight transition fails with a transitioning error
    covering the whole window, distinguishable by type, never reported as an unknown
    segment. A resolution from inside the transition is served normally so teardown can
    reach what it exists to tear down; the exemption ends with the transition.
  - The framework never waits for, tracks, or blocks on in-flight readers; draining
    belongs to the host that admitted the work.
  - The async start/shutdown is observably equal to the sync ones and awaits coroutine
    hooks and module initialize/teardown. The sync path refuses coroutines as a
    precondition — established before any lifecycle code runs — naming every offending
    hook or module, and returning the framework to inert. Discovery (configuration reads,
    module imports) is synchronous on both paths.
  - A busy transition is refused immediately by the async path, never waited for; the
    caller gets the already-in-progress error before the in-flight transition settles.
  - Rollback pairs hooks symmetrically: every module whose kind startup hook fired gets
    its kind shutdown hook fired, whether or not its own initialize completed.
  - Reaching inert is unconditional on any attempted transition out of started — registry,
    ordering bookkeeping, and loaded configuration reset, and a subsequent start accepted
    — whether or not app-authored code or the rollback succeeded. Where both a teardown
    failure and a rollback failure occur, the caller sees the app-authored one. A second
    shutdown after a failed shutdown is a harmless no-op.
  - App-authored lifecycle failures propagate with their original type and traceback,
    unwrapped; kernel-authored failures remain kernel errors. Propagating and reaching
    inert are never traded off.
  - Restart rebuilds kernel-owned state by re-running discovery — including after a failed
    shutdown — while the contract states that the runtime's module cache and module-level
    state persist: module-level code executes at most once per process, and the kernel
    makes no reloading claim.

#### project-configuration

- **Purpose:** One declarative file configures the project — mode, per-mode app cascade,
  plugins, per-mode environment values — and the kernel reads nothing else.
- **Must hold:**
  - The kernel reads exactly one declarative file at a conventional location under the
    project root. Missing file → documented defaults (development mode, no apps, no
    plugins) plus a warning; unreadable/unparseable → a configuration error naming path
    and reason, never a raw parser error.
  - The kernel's table has a closed key set: an unknown key fails start naming the key and
    the valid keys. The kernel claims exactly one top-level table, permanently; every
    other top-level table is application-owned, exposed as parsed data, never interpreted
    or silently discarded.
  - Loaded configuration is isolated per load — mutating one framework's exposed
    configuration never affects documented defaults or any later load.
  - Apps are declared per mode and cascade by a declared mode set (default: production →
    production; staging → staging, production; development → development, staging,
    production), preserving order with duplicates keeping first position. Unknown modes
    fail start naming the valid set.
  - Every app entry is a dotted module path importable by normal import, optionally with
    an explicit namespace (`"pkg.path as alias"`); the namespace derives from the final
    path segment unless stated. Unimportable paths fail start naming the path; the kernel
    never alters the import environment. Two apps resolving to one namespace fail start
    naming the namespace and both paths.
  - Plugins are configured registrations grouped by kind: the group must name a declared
    kind (never widening the closed set); unresolvable references and undeclared kinds
    fail start naming them. A plugin cannot claim a namespace another package owns. Kinds
    declaring a metadata contract fail start with a message stating configured
    registrations cannot satisfy it.
  - Environment values load from per-mode files in a conventional directory, falling back
    to a default file then to empty values; the fallback never depends on logging or
    verbosity settings.

#### kind-vocabulary

- **Purpose:** Publish a conventional default set of kind names with agreed meanings — a
  default, not a mandate — plus its one behavioral member, the resource lifecycle
  convention.
- **Must hold:**
  - One authoritative enumeration is published: each kind with its meaning and lifecycle
    role, alongside the rule that a project may declare any kinds it chooses and that the
    vocabulary is what reusable third-party apps may assume.
  - Every vocabulary kind name satisfies the identity grammar's kind rule; kind names and
    meanings agree across documentation, shipped template sets, and the reference
    application — one kind never means two things.
  - The resource lifecycle convention: components of the resource kind declare
    process-lifetime resources; the kind's startup hook makes each live before application
    code runs; any component reaches a live resource through ordinary registry resolution;
    the shutdown hook releases it. Expressible entirely through existing public kernel
    contracts — no dedicated resource API.
  - After shutdown, resolving a resource identifier fails with the registry's named
    resolution error — never yields a released resource.

### Typed access

#### typed-component-access

- **Purpose:** Let a caller state the type it expects when resolving a component by
  identifier, and be told at access time when the registry holds something of the wrong
  shape — without importing the declaring application.
- **Must hold:**
  - Typed access returns the identical registered object — never a copy, wrapper, or
    proxy — and is a pure lookup that never invokes or constructs it.
  - Typed access verifies at access time that the object's shape (constructible, value, or
    callable) matches the contract's expectation, failing with an error naming the
    identifier, expected shape, and actual shape. It deliberately does not verify
    structural member satisfaction — that belongs to static checking.
  - Obtaining a typed reference never requires importing the providing application's
    modules; the only coupling is the canonical identifier and the caller's own contract.
  - Adding a type contract never coarsens resolution failures — they remain per-segment
    with candidates.

#### typed-registry-navigation

- **Purpose:** Reach a component by walking the identity grammar's three facets as typed
  members, so a type checker can describe every step at any registry size.
- **Must hold:**
  - The navigation steps are the grammar's facets in order (kind → namespace → object
    name); every registered component is reachable by exactly one path and no path exists
    for an unregistered component. The surface is derived from the registry, not
    separately declared — nothing is stated twice.
  - Navigation yields the identical registry record that resolving the canonical
    identifier yields, never invokes or constructs the object, and observes the same
    read-consistency rules as identifier resolution, including during lifecycle
    transitions.
  - A failed navigation step fails at that step naming the segment and the candidates —
    the same precision identifier resolution provides.
  - A segment whose name is a host-language reserved word remains navigable through one
    documented, deterministic escape spelling applied identically at runtime and in the
    static description; the canonical identifier never changes.
  - The generated type description expresses navigation as nested typed members: a valid
    path yields the component's concrete static type; an invalid path is a static error
    naming the failing member — both holding within the declared checker set regardless of
    registry size (verified at tens of thousands of components).

#### typed-registry-stubs

- **Purpose:** Describe the project's own resolution surface as an inert static artifact
  produced by dry-booting, so editors and type checkers know what `resolve` returns for
  each identifier.
- **Must hold:**
  - Describing a project registers apps and runs discovery without invoking module
    initializers, teardown, or lifecycle hooks; it leaves no observable effect and returns
    the framework to its pre-description state, including after failure.
  - The description contains exactly one entry per registered canonical identifier and
    none for unregistered identifiers. The described identifier set derives from the
    project's own registry projection, so stub and projection cannot disagree;
    language-specific detail stays in the description and out of the language-neutral
    projection. Configuration-registered components appear on equal terms.
  - Each entry records which of the three shapes the object is — constructible, value, or
    callable — and states a static type consistent with it.
  - An undescribable type degrades to the unconstrained type, never an inferred or
    approximate one; degraded entries remain present and resolvable, and the degraded
    count is available to the caller.
  - The generated description is inert at runtime: never imported or executed by the
    running project; deleting it changes no behavior.
  - Generation is deterministic — byte-identical output for the same unchanged project,
    entries in canonical identifier order, unaffected by declaration order.
  - A verification mode regenerates and compares without modifying the stored description,
    reporting mismatch on any gained/lost/type-changed component and on a missing stored
    description.
  - The description is diagnostic-free under every checker in the declared conformance set
    (mypy, pyright, ty), in every emission mode, with any needed suppression carried by
    the description itself; conformance is verified by actually reading each mode with
    each checker, not asserted from generator output.
  - Above a documented entry-count threshold, the generator reports the count, the
    threshold, and the supported alternative surface — while still writing the
    description; below it, silent and byte-identical.

#### static-type-soundness

- **Purpose:** Make the package's published type information verified rather than
  asserted, with deliberate dynamism named, scoped, and countable.
- **Must hold:**
  - The published package source passes a mature static type checker in its strictest
    standard mode as a standing row of the validation gate; a beta checker may run beside
    it but never as the only gate. Disagreement between gating checkers is a finding about
    the source, never resolved by loosening a checker.
  - The strict check runs on every declared platform and supported interpreter with the
    same configuration and outcome expectations.
  - Every public surface that registers or marks an object and returns it preserves the
    object's static type at the registration site and every later use — erasing it is a
    defect.
  - Checker exemptions are scoped to the narrowest unit the toolchain allows, carry an
    in-place justification, and are fully enumerable from configuration — never scattered
    inline suppressions. Widening an exemption's scope requires its own recorded
    justification.

### Data

#### format-codecs

- **Purpose:** Normalize every supported data format to one intermediate representation —
  the JSON data model — so consumers are written once rather than once per format.
- **Must hold:**
  - Reading any supported format produces only JSON-model values; no format-specific node
    or parser object crosses the boundary. Writing accepts the same model. Read → write →
    re-read is equal for every writable format; cross-format conversion needs no per-pair
    rule.
  - Every format is readable from an in-memory string and from a path with identical
    results; format is inferred from the extension, overridable by explicit declaration.
    An unknown extension with no declared format fails naming the extension and listing
    supported formats.
  - A format requiring an optional dependency never fails at import; the failure occurs
    when the format is first requested and names the optional extra to install.
    Standard-library formats work with nothing optional installed. Availability is settled
    on first probe and stable for the process.
  - Read and write support are declared per format independently; an unsupported direction
    fails naming that direction and what would enable it. Supported directions are
    enumerable per format for the current environment.
  - Tabular data reads as an array of objects keyed by the header row (W3C csv2json
    minimal mode) — an array even for a single row. Every value reads as a string (no
    type inference); the lexicographic-comparison consequence is documented. A row whose
    cell count differs from the header fails the read naming the row.
  - Writing a value the target format cannot express fails with the surface's own error
    family naming the format and the value — no underlying serializer error reaches the
    caller. Writing to a path with missing parent directories creates them.
  - Hierarchical markup reads as nested objects with attributes and element text
    distinguishable by a stated convention. Repetition is resolved from caller-declared
    paths, never inferred from occurrence count; a declared-repeating path yields an array
    at zero, one, or many elements. Lossy aspects are stated as declared limits.

#### data-collection

- **Purpose:** Resolve a directory tree of mixed formats to one mapping in a single call,
  with location-derived keys, loud collisions, and eager all-or-nothing loading.
- **Must hold:**
  - One collection operation resolves a tree of differing supported formats into one
    mapping. Unsupported extensions are skipped (reportable); an existing empty directory
    is a valid empty collection; a root that does not exist or is not a directory fails
    naming the path.
  - Hidden entries (leading dot) are skipped by default; explicit ignore patterns extend
    the skip set. Skipping happens before key derivation; a skipped directory is skipped
    as a unit — never traversed — and the reportable skipped set names the directory
    itself and nothing beneath it, ordered deterministically.
  - Each entry's key is its path relative to the root with the extension removed and
    separators replaced by dots, independent of source format. Every key segment satisfies
    the identity grammar; a violating name fails the collection naming the offending value
    and the grammar.
  - Two files producing the same key fail the collection naming both paths — never
    resolved by format precedence, ordering, or merging.
  - Collection is eager and all-or-nothing: every file fully read and normalized before
    returning; a parse failure fails the whole collection naming path and reason; no
    partial mapping.
  - The collection surface is never invoked by framework startup and never imported by the
    kernel; removing it leaves startup, configuration, discovery, identity, and resolution
    identical and the install footprint unchanged.

#### data-access

- **Purpose:** Two separate ways to reach into the intermediate representation — exact
  addressing (RFC 6901 JSON Pointer) and querying (RFC 9535 JSONPath) — kept apart
  because their failure semantics differ.
- **Must hold:**
  - Exact addressing resolves to exactly one value or fails naming the unresolvable
    segment; never a null, empty result, or default. Absent and null-valued are
    distinguishable.
  - Querying returns a possibly-empty result set; an empty result is never an error.
    Conformance is verified against RFC 9535's published compliance suite, with any
    narrowing (disabled non-standard syntax) pinned by verification.
  - Malformed addresses/queries fail through the surface's own declared error family — no
    underlying implementation's error type reaches the caller.
  - The two modes are not configurable into each other: no option makes a query raise or
    an exact address silent.
  - Both modes behave identically regardless of source format, including for entries
    obtained from a collection.

### Scaffolding

#### project-scaffolding

- **Purpose:** Define what a scaffolding operation produces and what it refuses: a project
  that starts unedited, and refusals that prevent clobbering, partial trees, and invalid
  names.
- **Must hold:**
  - One operation produces a complete project that starts with no edits — configuration
    file, framework declaration, one app, an entry point, and an origin record — with
    names agreeing across all of them.
  - Derived source-level names are legal in the generated language and distinct from every
    other derived name; no name the identity grammar accepts is refused because the
    generated language reserves it.
  - The operation refuses to overwrite content it did not create, naming the conflicting
    path, and never leaves partially written trees on failure. The target directory must
    be empty or absent.
  - Names are validated against the identity grammar before any content is written. Escape
    detection covers every path form the host resolves — relative traversal with either
    separator, absolute, drive- or root-qualified — in the validation step, applying
    equally to template-set-supplied paths.
  - The scaffolder never alters the kernel's dependency footprint; the kernel never
    depends on the scaffolder at runtime; removing the scaffolder leaves the kernel
    intact.
  - Adding an app to an existing project generates a package matching what project
    generation emits, refuses when the app exists (writing nothing), leaves the
    configuration byte-identical while stating the exact entry to add, derives kinds from
    the project's framework declaration when unstated (stated kinds override; neither
    present fails actionably), and reports template-set divergence without divergence
    preventing the operation.

#### scaffold-templates

- **Purpose:** Define what a template set is and what it may do — declared data, resolved
  by an explicit discriminator, validated before any file is written, never executed.
- **Must hold:**
  - Emitted content is declared data stored in files of the format they are emitted as,
    not literals in program code; changing the generated project's shape requires only
    data changes.
  - A template set is replaceable and identified explicitly, with exactly one in effect
    per operation; the built-in set is the default. Unknown references fail naming the
    reference and listing resolvable candidates, writing nothing.
  - A reference resolves as a filesystem directory, an importable package, or a remote
    location, decided by an explicit discriminator evaluated in a fixed order — before
    existence is consulted, never depending on what happens to exist locally.
  - Validation runs before anything is written and is bounded in both directions: the set
    must supply everything required and must not claim any destination reserved to the
    generating operation. Validation never varies with origin.
  - Substitution values are a declared, enumerable set; rendering never executes code
    carried by the template set. Origin grants no additional capability — no hooks, no
    expression evaluation — and this guarantee is stated to the caller.

#### template-provenance

- **Purpose:** What a generated project records about its own origin, and how a later
  scaffolding operation uses it to notice a template-set mismatch. The record is advisory
  throughout.
- **Must hold:**
  - Generation emits an origin record naming the template set reference and, where
    applicable, the exact resolved revision; it is part of the generation plan (same
    never-overwrite / all-or-nothing guarantees).
  - Emitting the record is the generating operation's own obligation: a template set
    cannot prevent, supply, alter, or substitute into it.
  - The record is a standalone declarative data file, readable without executing the
    project, and never affects whether the project starts — removing it leaves a runnable
    project; adding an app leaves the project's configuration byte-identical.
  - The record's destination is reserved: any template set claiming it is refused before
    anything is written, identically regardless of origin.
  - An operation adding to an existing project compares its template set against the
    recorded origin and reports divergence naming both, but never fails on divergence
    alone. An absent or unparseable record is unknown origin, never a failure.

#### remote-template-acquisition

- **Purpose:** Define how a template set named by a remote location is parsed, pinned,
  retrieved, bounded, admitted, and retained. Retrieved content is treated as hostile
  throughout.
- **Must hold:**
  - Every reference resolves to exactly one kind of source by an explicit discriminator in
    fixed order, before existence is consulted. No fall-through to a later kind on load
    failure: "failed to resolve" and "resolved then failed" are distinct outcomes reported
    distinctly.
  - A remote reference is resolved to an exact, immutable revision before any content is
    retrieved; a moving target's resolved revision is reported in a form that can be
    supplied back. Same reference + same revision → identical content.
  - Retrieval, admission, and validation all complete before any file is written to the
    destination; any failure leaves the destination untouched. A failure names the
    reference as the caller supplied it. Retrieved sets are validated exactly as local
    ones.
  - Every member of retrieved content is individually admitted: refused when its path is
    absolute, escapes the destination by any means, or is not a regular file or directory.
    Containment is decided by path structure, not string prefix, and verified
    independently of the platform's own extraction vetting. No remote-supplied name may
    construct any local path; the container format is determined from content, never a
    name.
  - Retrieval is bounded on expanded size and member count, enforced before the excess is
    materialized and against what actually expands. A redirection onto a location with
    weaker guarantees than the supplied reference is refused.
  - Content retrieved for an exact revision is retained and reused: repeat generation
    performs no retrieval; a retained revision remains usable when retrieval is
    unavailable; an unretained revision without retrieval fails actionably. An interrupted
    retention never appears retained.
  - A revision designates its own retained content and no other's: two distinct revisions
    never share retained content; sameness of locations is judged by the store, not by
    textual difference — a revision whose name the store would alter, fold, or share takes
    a derived name (the host filesystem's case folding and trailing-dot stripping are part
    of "the store").
  - Concurrent retention of one revision converges: both operations succeed and observe
    complete content; the loser leaves no staged content; a genuine publish failure is
    never disguised as a race.
  - Retained content lives in the host platform's per-user cached-data location,
    overridden by a user-stated cache location, namespaced to this project.

#### starter-templates

- **Purpose:** A shipped starter template set that turns `init` from a skeleton generator
  into an application generator, yielding a running, transport-neutral project.
- **Must hold:**
  - The starter ships alongside the minimal default set, resolvable by name under the same
    reference rules, held to every template-set contract. Selection is explicit; the
    minimal set remains the default.
  - A generated starter project starts unedited, declares the conventional kind
    vocabulary, and includes: a transport-neutral projection module deriving surface
    tables from registry records alone, a runnable project-owned command surface derived
    through that projection, a resource under the resource lifecycle convention, and a
    dispatch site for surface-invoked hook components.
  - The generated project requires no third-party dependency to start or run its command
    surface, binds to no specific transport, and generating/running it adds no runtime
    dependency to the kernel's distribution.
  - Projected surfaces correspond one-to-one with registry records; declaring one
    additional component of a projected kind extends the projected tables and command
    surface without editing the projection or surface modules.

### Tooling and CLI

#### project-diagnostics

- **Purpose:** Validate a project's declaration before runtime and make its registry
  inspectable without writing a script — check, list, and explain; library-first and
  fully isolated.
- **Must hold:**
  - **check** validates, leaving no running state behind: configuration syntax and typing,
    mode validity, resolvability of every declared app and plugin reference, kind
    dependency acyclicity, identity uniqueness, and lifecycle hook compatibility with the
    synchronous path (flagging coroutine hooks under a sync entry point by name). Every
    finding carries the same precision as the corresponding runtime failure. Exit status
    is zero on a clean report, non-zero otherwise.
  - **list** boots the declaration, enumerates every registered record's canonical
    identifier (optionally narrowed by kind or namespace), and tears the boot down
    completely. Kind narrowing is answered by reading that kind's facet, not by
    enumerating everything and discarding. An unknown kind fails naming valid kinds; an
    empty namespace is an empty result, not a failure.
  - **explain** resolves one canonical identifier and reports the record's kind,
    namespace, object name, and the registered object's identity/location; resolution
    failures are the kernel's own precise errors with candidates, and a non-zero exit
    status.
  - Operations locate the framework declaration by the same convention the project
    generator emits, accept an explicit module-and-attribute override, and, when neither
    works, state what was searched and the override syntax.
  - Each operation is invocable as a plain library call returning structured results; the
    CLI only parses, invokes the same operation, and renders — both report the same
    findings.

#### registry-projection

- **Purpose:** Describe a booted registry as data under a published schema so consumers
  that never import the project can read what it registered.
- **Must hold:**
  - There is exactly one projection, and every surface describing the registry derives
    from it. Per component: canonical identifier, the three facets, where the registered
    object is defined, and the object's shape — plus the project's declared kind set
    (including kinds with no components). It carries nothing requiring the consumer to
    share the framework's language.
  - The projection has a published schema in a standard schema language, obtainable and
    validatable without executing project code; every emitted document validates against
    it. The document states the projection format's version, independent of the
    framework's release version.
  - Producing a projection requires only discovery (configuration, app loading,
    registration), never lifecycle initialization or startup hooks — so a project whose
    startup would fail is still describable. A discovery failure remains a failure with
    the framework's own error unchanged.
  - Entries are emitted in canonical identifier order; two projections of one unchanged
    registry are byte-identical, and no value varies between runs (no process-specific
    values such as memory addresses). Reordering the installed-app list changes nothing.
  - The projection is obtainable both as a library result and via a command that is a thin
    adapter over the library operation, producing the same content and ordering on
    standard output.

#### cli-command-mounting

- **Purpose:** Let a downstream framework publish this system's command groups under its
  own program name via a defined mount extension point.
- **Must hold:**
  - Every shipped command group is mountable onto a caller-constructed parser; the
    mountable groups are exactly those the shipped program composes — project generation,
    project diagnostics, registry projection, and stub generation — and the shipped
    program obtains them by the same mount (no privileged assembly path).
  - A mount is additive: it contributes its commands and leaves existing commands
    untouched; several groups compose without redefining each other's commands.
  - A mount never reads process arguments, writes to process output streams, or ends the
    process. Parsing, dispatch, and translating outcomes into a process result remain the
    caller's responsibility.
  - The generation group accepts at mount time two optional composition-root derivations —
    how a project's kinds derive from its declaration, and how a template reference
    resolves to a template set. Omitting either falls back (kinds stated on invocation;
    locally installed template sets) rather than failing.
  - The contract promises the commands (names, arguments, effects), not the shape of the
    parser object; the parser type may change under the mount point's tier.

### Testing

#### test-harness

- **Purpose:** Ship the machinery a downstream project needs to test an application on the
  kernel — isolated construction with guaranteed teardown, declarative app-tree building,
  and mode override.
- **Must hold:**
  - The isolation scope yields a freshly constructed framework bound to a project tree
    and, on normal or exceptional exit, shuts it down and restores module import state and
    import search paths; exceptions propagate unchanged. Consecutive scopes are
    independent — no registry records leak between them.
  - The harness is usable with no test runner present, depending only on the standard
    library and the kernel's public contracts. Importing the root package or any kernel
    module never imports the harness.
  - A declarative builder materializes a bootable project tree (apps, modules with source,
    project configuration) without the caller knowing on-disk layout conventions.
  - A mode-override scope runs its body under a stated mode and restores the prior
    configuration on exit.

#### pytest-integration

- **Purpose:** Expose the test harness's pieces as pytest fixtures via standard plugin
  discovery, shipped in the one distribution.
- **Must hold:**
  - The distribution exposes the isolation scope, app-tree builder, and mode-override
    scope as fixtures resolvable by name with no extra package and no manual registration.
  - Harness teardown runs in full even when a test using the fixture fails; subsequent
    tests observe no leaked state.
  - The plugin never makes the test runner a runtime dependency: importing the root
    package without pytest installed succeeds and loads nothing from the plugin.

### Documentation and examples

#### documentation-integrity

- **Purpose:** Make it mechanically impossible for published documentation to drift from
  the code it documents.
- **Must hold:**
  - Every code example in published documentation is either executed by the test suite or
    carries an explicit, machine-readable non-runnable marker. Published documentation
    includes the repository README (front page and distribution long-description), held to
    the same bar as the docs site.
  - An example presuming a project on disk is supplied that tree by the project's own test
    harness and runs unmodified; an example showing declaration-then-resolution presents
    the declaration where discovery actually reads it from and resolves as shown.
  - An example whose value is its output displays that output beside the code, verified
    against actual execution, with regeneration mechanical rather than a manual edit.
  - API reference member listings derive from the package's own declaration of its public
    surface, so additions and removals propagate with no documentation-side edit.
  - The CLI reference page's commands, flags, and help text are generated at documentation
    build time from the same parser the shipped command uses.
  - The documentation contains an error index covering every publicly exported exception
    type with its trigger, its fix, and a link to the underlying concept, verified
    complete against the declared public surface — a new unindexed exception fails the
    gate.

#### framework-tutorial

- **Purpose:** Convert the "simple enough to build a framework on" claim from a slogan
  into an executable, test-gated documentation page.
- **Must hold:**
  - The documentation contains a tutorial starting from an empty directory that produces a
    running framework: declaring the kind set, writing at least one application component,
    and projecting the registry onto a transport that serves a real request. Each step
    shows the complete file; the final step shows a real invocation and its actual
    response.
  - The payoff is observable — a request against a reader-authored framework returning a
    response derived from a registered component, not a printed identifier list.
  - The tutorial's accumulated code is assembled and executed by the test suite as
    presented (same files, same order), including the final request/response assertion, so
    drift fails the gate naming the tutorial.
  - The tutorial framework requires no third-party packages — every step runs on a bare
    kernel install.

#### reference-application

- **Purpose:** Carry one runnable reference project in the repository, booted by the test
  suite, so the worked example cannot drift from the kernel.
- **Must hold:**
  - The reference project runs unedited and demonstrates every public kernel contract a
    downstream project composes: several apps across modes, cross-namespace runtime
    resolution, plugin-configured registrations, and a surface projected purely by
    enumerating the registry (every route corresponds to a registry record).
  - It includes both a synchronous entry point and an asynchronous one whose declaration
    carries coroutine hooks, each booting and shutting down on its own path.
  - The test suite boots the project and exercises its behaviors so kernel-induced drift
    fails the standard gate; CI constructs the real HTTP application object rather than
    skipping for a missing dependency.
  - It demonstrates the resource lifecycle convention using only public kernel contracts,
    with the suite observing both open and release.

### Governance

#### public-api-surface

- **Purpose:** Define which published artifacts carry a stability promise, what each tier
  guarantees, and make the declared surface verifiable against the real one.
- **Must hold:**
  - Every surface element carries exactly one tier from the closed set `public`,
    `provisional`, `internal`; the surface spans importable names, executable commands and
    their machine-readable output, plugin registrations, named optional dependency groups,
    configuration file schemas, and generated-file contracts. An undecided element is
    `internal` — absence of a promise is never read as a promise.
  - For importable elements the tier follows from total rules read from the artifact alone
    (no external list): exposed only from an inner unit → `internal`; carrying the
    provisional notice → `provisional`; otherwise exposed from a published namespace →
    `public`. Non-importable element kinds have their tier declared explicitly, and the
    set of such kinds is stated.
  - Exposure from a published namespace must be justified by one of four admissible
    reasons (an operation invoked, a contract implemented/substituted, a condition
    distinguished, a value supplied/read/compared). Internal composition detail and
    breadth of internal reuse are not admissible; an unjustified exposure is corrected by
    withdrawal.
  - Where a consumer must reference several elements to complete one offered path, every
    element of that path carries a stated tier; a wholly unpromised path is coherent, a
    half-promised one is defective.
  - Tier guarantees: `public` — incompatible change only in a major release after the
    deprecation lifecycle; `provisional` — may break in a minor without deprecation, never
    in a patch; `internal` — may change in any release. Raising a tier is always allowed;
    lowering is itself an incompatible change. Reachability never confers stability.
  - The tier is visible at the element's point of definition without consulting another
    file; `provisional` elements additionally state that they may break in a minor release
    and what would settle the tier.
  - Withdrawal is marked readably from the artifact without executing it, naming the
    replacement or stating there is none, in the same place the tier is readable.
    Withdrawal is not a tier: a marked element keeps its tier and every promise until
    removal. Withdrawal is expressed through exactly one mechanism.
  - The contract enumerates its exclusions, at minimum: error/log message wording (types
    and hierarchy are public), human-readable prose command output (machine-readable is
    public), resolved dependency versions inside a named optional group, and internal
    attribute names of public types.
  - A check establishes every element's tier in standard validation without publishing a
    release, failing on: elements matching no rule or more than one, undeclared
    non-import elements, and declarations naming absent elements.
  - Establishing a completed deprecation lifecycle reads the project's published releases
    to find the release that first marked the element, measuring the waiting period in
    minor releases (a patch never satisfies it).
  - Coverage gaps and undeterminable withdrawal histories are reported as
    unverifiable/undetermined — never inferred, never reported as absent or compliant —
    with their counts in the output, so a passing run never implies coverage it lacked.

#### release-policy

- **Purpose:** Bind version numbers to the stability tiers of the public API surface:
  what each increment asserts, how elements are withdrawn, what releases record, and when
  the project may declare itself stable.
- **Must hold:**
  - SemVer increments assert exactly: patch — nothing above `internal` changed
    incompatibly; minor — no `public` element changed incompatibly (`provisional` may
    have); major — `public` may have, each having completed deprecation. Ambiguity
    resolves to the larger increment.
  - The assertion is checkable: a check compares the working tree's surface against the
    previous released artifact, classifies every difference compatible/incompatible,
    reports newly exposed elements as additions, runs in standard validation, and fails
    when a difference is incompatible with the claimed increment.
  - A single explicit pre-stable allowance (public elements may break in a minor before
    1.0 without deprecation) is published wherever the policy is, and ends the moment the
    first stable major is cut; it is never extended by re-releasing pre-stable.
  - After the allowance ends, a `public` element completes the deprecation lifecycle:
    marked deprecated with replacement named (or explicitly none), a runtime deprecation
    signal a consumer can suppress or escalate, present and functional for at least one
    full minor release, then removable only in a major. Deprecation and removal never
    share a release; enforcement is by the same comparison, not reviewer memory.
  - Every release records in published history each observable surface change —
    additions, deprecations (recorded when marked, not when removed), removals, tier
    transitions, and every incompatible change stated in terms of what a consumer must do.
  - Stable-release criteria are published, objectively determinable, and include at
    minimum: every element tiered and the surface check passing; nothing intended
    `public` still `provisional`; the deprecation lifecycle implemented and exercised.
    Criteria are never weakened in the change that cuts the release.

#### platform-support

- **Purpose:** Define which platforms behavior is guaranteed on, and make the guarantee
  evidence rather than assertion — declaration, gate, and documentation must agree.
- **Must hold:**
  - The project declares its supported platforms in one place, and that declaration is the
    single source the validation gate and its consumers derive from. A platform absent
    from the declaration is not supported and is never claimed; documentation names no
    platform outside the declared set.
  - Admitting a change requires the gate to have passed on every declared platform; a
    proper subset is never sufficient, and a missing leg is reported as absent rather than
    assumed to pass. Inherently platform-independent checks may run on one platform.
  - Platform-conditional behavior is verifiable from any host: every platform-conditional
    branch is reachable in a single run of the suite on any one declared platform, so the
    set of exercised branches is identical across platforms and coverage does not depend
    on the measuring host.

## Decisions

Every build-vs-adopt decision that shaped the system lives in `DECISIONS.md` at the
repository root — one full-length record per decision, IDs `D01`–`D60`, with the
rationale, the alternatives considered, and the isolation seam for each. The toolchain
those decisions picked is declared where it is enforced: `pyproject.toml` and
`Taskfile.yml`.
