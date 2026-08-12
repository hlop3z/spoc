## Context

Three surfaces already describe the registry, at three boot depths, in three shapes.

`diagnostics.list_records` boots fully — configuration, discovery, initialization, hooks —
and returns `RecordInfo(identifier, kind, namespace, object_name, location)` for human
reading through `spoc list`. `stubs.manifest.describe` boots one phase earlier, stopping
after discovery, and returns `Manifest` holding `Entry(identifier, kind, namespace,
object_name, shape, type_ref)` for the `.pyi` emitter. `Registry.all()` underneath both
returns `Component` records sorted by canonical identifier.

Four fields are common to both descriptions. Neither can leave the process: `RecordInfo`
has no serialization, and `Entry` is consumed only by a text emitter whose output is Python
source. The result is that a consumer outside Python has exactly one option, which is to
parse the `.pyi` — an interface nobody designed, whose stability rules exist for type
checking and would then have to serve data extraction too.

The collect-only boot is the interesting precedent here. `stubs` deliberately stops before
initialization because describing a project should not require its startup hooks to
succeed; a project whose `models` hook opens a database connection can still be described
on a laptop with no database. That property is worth more to a data projection than to a
stub, and it is the reason the projection is not simply `--json` on `spoc list`.

## Goals / Non-Goals

**Goals:**

- One description of the registry, produced once and consumed by every surface that needs
  one.
- A document that validates against a published schema, so a consumer in any language can
  check what it received.
- Describable without initializing the project, so the projection works where a full boot
  would not.
- Ordering and content rules stated well enough that two projections of one registry are
  byte-identical, and a diff means something.
- A deliberate public data contract, entered knowingly before the stable release rather
  than inherited from whatever people started scraping.

**Non-Goals:**

- Replacing `spoc list`. Human diagnostics and machine projections have different audiences
  and different boot depths; see Decision 1.
- Carrying Python type references in the projection. `type_ref` is a Python-specific concern
  of the stub emitter and has no meaning to a consumer in another language; see Decision 3.
- A projection that can be loaded back to reconstruct a registry. This describes; it does
  not serialize objects, and the kernel still never executes what it describes.
- Routing through `spoc.formats`. The kernel's own surfaces use `json` from the standard
  library directly, and the containment boundary between kernel and `formats` stays as it is.
- Watching, diffing, or caching projections. Those are consumers' jobs.

## Decisions

### Decision 1: A separate surface at a separate boot depth, not `--json` on `spoc list`

`spoc list` boots fully and prints for humans. The projection describes after discovery
only and prints for programs. Adding `--json` to `list` would either force the projection
to require a full boot — losing the property that makes it usable in CI and in editors — or
give one command two boot depths depending on a flag, which is worse than two commands.

The Rule 7 tension is real and should be named rather than waved off: three surfaces over
one registry is a lot. The consolidation this change performs is at the *data* layer, where
`RecordInfo` and `Entry` collapse into one projection; the *commands* stay distinct because
they answer different questions. If `spoc list` later becomes a formatter over the
projection at full boot depth, that is a further simplification this decision does not
foreclose.

**Resolved during implementation (task 4.5):** the data layer consolidated all the way, and
`RecordInfo` is gone. The `registry-projection` spec's own scenario forced it — *no second
structure describing the same components exists* — and `RecordInfo` was one. `list_records`
and `explain` now return `ComponentEntry`, still at full boot depth, so only the rendering
and the boot depth distinguish `spoc list` from `spoc projection`. The commands stay
distinct, exactly as this decision holds.

Deleting it also deleted a live defect rather than merely a duplicate. `RecordInfo` derived
an object's location from its `repr` when it carried no `__qualname__`, which for a
registered *instance* embeds a memory address. In prose output that was untidy; the moment
the same rule reached a document meant to be diffed, it made two projections of one
unchanged registry differ. The projection locates an instance by its type instead, and that
is now the only such rule in the codebase.

### Decision 2: The projection is a format, not a Python type that happens to serialize

The published artifact is the JSON document and its JSON Schema. The Python dataclass is
one producer of that document, and its field names follow the document rather than the
reverse. This is the difference between a format other systems can implement and an API
they must mirror, and it is the entire long-horizon argument for the change.

Rule 9 chooses JSON Schema. The alternative — a bespoke description in prose plus an
example — is what every framework does and is why every such format drifts.

### Decision 3: Shape travels, type references do not

Shape — constructible, callable, or value — is a property of the registered object that any
consumer can act on, and the vocabulary already exists in `ComponentShapeError` and in
typed access. A Python type reference is meaningful only to a Python type checker, degrades
to `Any` when it cannot be determined, and would put a language-specific concern into a
format whose point is to outlive the implementation.

So `shape` moves into the projection and `type_ref` stays in `spoc.stubs`, where the stub
emitter computes it from the same live objects it does today. The stub's manifest becomes
the projection plus the Python-specific extras it needs.

### Decision 4: Canonical-identifier order, restated rather than assumed

The projection emits in canonical-identifier order, for the reason
`typed-registry-stubs/spec.md` already gives: an unrelated change must not churn a
committed artifact. This is stated in the projection's own spec rather than inherited by
proximity, because a consumer diffing two projections needs the guarantee to be about the
projection.

### Decision 5: Versioning the document, not just the code

The document carries the projection format's own version, independent of the SPOC release
version, so a consumer can branch on the format without inspecting the producer. The
release policy governs when that version may change incompatibly; the point of stating it
in the document is that a file found on disk years later still says what it is.

`/ai:decide` runs before implementation and should settle at minimum: whether the schema is
hand-written or generated from the producer, and whether an existing vocabulary (Rule 9's
Schema.org/RDF direction) has anything to offer a component registry, or whether this is
sufficiently domain-specific that JSON Schema alone is the whole of the adoption.

## Build-vs-Adopt Decisions

Recorded by `/ai:decide`; mirrored project-wide in `DECISIONS.md`. Concrete tool names live
here and there only — `specs/` stays abstract.

### Decision: The schema language — Adopt JSON Schema, draft 2020-12, hand-written

- **Status**: approved
- **Why**: Rule 9 settles the language; what the gate had to settle is authorship and the
  draft. The document is pinned to `https://json-schema.org/draft/2020-12/schema`, the
  current published draft — its successor is still an unexpired IETF Internet-Draft
  (`draft-ietf-jsonschema-json-schema`, July 2026), so pinning to it would pin to something
  that can still change. 2020-12 is fully supported by every validator a consumer is likely
  to reach for in any language.

  The schema is **written by hand and checked in**, because Decision 2 above makes the
  document the format and the Python dataclass one producer of it. A generator inverts that:
  the dataclass becomes the authority and the published contract becomes its shadow. It also
  cannot express the parts that carry the most meaning — the `kind:namespace.object_name`
  pattern, the closed shape vocabulary, and a format version deliberately independent of the
  release version — without annotating the dataclass into a schema DSL, which is the
  inversion again by another route.
- **Considered**: `dc_schema` (tiny, stdlib-only, emits 2020-12 — the closest fit if
  generation were wanted, but a micro-library with thin maintenance signal, and it inverts
  Decision 2); pydantic (mature and 2020-12 capable, but it lives in the `examples`
  dependency group today and this would promote it to a build-time dependency of the
  published artifact — heavy for one static document, and the same inversion); draft 07
  (broadest legacy tool support, rejected as legacy for a format whose whole point is to
  outlive the implementation).
- **Drift control, since hand-writing is a restatement**: this is the one real cost, and it
  is paid by verification rather than generation — task 3.2 validates every projection the
  suite produces, task 3.3 asserts a malformed document fails, and a parity test asserts the
  producer's field set equals the schema's `properties`/`required` keys. That last one is
  the mechanical check that makes the restatement safe; without it, hand-authoring is a
  standing invitation to drift.
- **Isolation**: the published schema file plus the projection module that produces the
  document. Consumers validate against the file; nothing in the kernel imports a validator.

### Decision: Validating the projection in the suite — Adopt `jsonschema`, dev group only

- **Status**: approved
- **Why**: Standard-format validation is on the never-hand-roll list, so the question is
  which validator, never whether to write one. `jsonschema` (python-jsonschema, 4.26.0,
  January 2026) is the reference implementation, has full 2020-12 support, is pure Python,
  and therefore installs across the whole gated platform matrix without a wheel question.
  It lands in the `dev` dependency group on the same precedent as `hypothesis` and
  `pytest-examples`: `dependencies` stays empty and no downstream framework inherits it.
- **Reconciles with the earlier rejection, deliberately**: "Configuration validation —
  Adopt `tomllib`, build the four-key check" rejected `jsonschema` outright, for pulling
  attrs, referencing, and rpds-py to describe a four-key contract. That rejection stands and
  is not reversed here. Two things separate the cases. It was a *runtime* dependency there
  and is a *test* dependency here, so the zero-`Requires-Dist` invariant that drove it is
  untouched. And that ADR scoped Rule 9 to "contracts and identifiers exchanged with the
  outside world, not a four-key internal config file" — the registry projection is precisely
  such a contract, which is why the same rule now points the other way on the same tool.
- **Considered**: `jsonschema-rs` (Rust-backed and much faster; throughput is irrelevant for
  a suite validating small documents, and a compiled extension adds wheel risk across three
  OSes and three Python versions); `check-jsonschema` as a CLI in `.canon/checks.md`
  (matches the tokei/`ensure` adoption precedent, but the suite builds projections in
  `tmp_path` and a CLI forces file marshalling for every case, including the negative ones).
- **Isolation**: the test module that asserts conformance. No source module imports it, and
  the schema file remains validatable by any external tool.

### Decision: Domain vocabulary — none applies; JSON Schema is the whole adoption

- **Status**: approved
- **Why**: Rule 9 points at Schema.org/RDF for vocabularies, so the question was asked
  properly and the answer is negative. Nothing standard describes *what an application
  registered in-process*. Schema.org `SoftwareApplication` describes software products for
  search and discovery. SPDX (ISO/IEC 5962) and CycloneDX describe dependency inventories
  keyed by Package URL, for licence compliance and supply-chain use. OpenAPI and AsyncAPI
  describe API surfaces. Each models a different subject; adopting one would mean bending
  this format to a vocabulary that does not fit it, for interoperability no consumer would
  actually exercise.
- **Recorded so it is not re-asked**: the negative answer is the deliverable of task 1.2.
  The revisit trigger is a change of subject, not of scale — if the projection ever
  describes *packages* rather than in-process components, CycloneDX plus purl is the thing
  to adopt at that point.
- **Considered**: aligning field names with Schema.org properties for familiarity (buys no
  interoperability while constraining the format's naming to an ill-fitting vocabulary;
  `shape` has no analogue at all).
- **Isolation**: not applicable — this decision adds nothing to adopt.

### Decision: Serializing the document — Adopt the standard library's `json`

- **Status**: approved
- **Why**: Standard-format serialization is on the never-hand-roll list and the standard
  library already covers it, so there is nothing to acquire. This also holds the containment
  boundary the proposal states: `spoc.formats` is a contained subpackage the kernel never
  imports, and the kernel's own surfaces already use stdlib `json` directly — `scaffold`'s
  provenance and remote-template modules are the existing precedent. Routing the projection
  through `formats` would make an optional-extra subpackage load-bearing for a core surface.
- **Considered**: `spoc.formats` (rejected on the containment boundary, not on capability);
  any third-party JSON encoder (rejected — nothing to gain, and `dependencies` stays empty).
- **Isolation**: the projection module's emitter. Task 1.3 is the test that pins the
  boundary.

## Risks / Trade-offs

- **A public data format is a long promise.** That is the point of the change, and it is
  still a cost: after 1.0 the document shape falls under the stability contract and can only
  grow. Mitigated by keeping the initial document small — the grammar's three facets, a
  location, a shape, and the kind set — and by refusing `type_ref` now rather than removing
  it later.
- **Three surfaces over one registry.** Named in Decision 1. The data layer consolidates;
  the command layer does not. If that proves to be one command too many, `spoc list` is the
  one to fold in, and this design leaves that open.
- **Collect-only description can differ from full-boot reality** if a startup hook or a
  ready callback registers components. Ready callbacks run during discovery, so they are
  included; anything a hook registers after initialization is not, and the spec must say so
  rather than let a consumer assume completeness.
- **Deriving the stub from the projection couples two release cadences.** Acceptable
  because both live in one distribution — the one-distribution rule means there is no
  version skew to manage — but a change to the projection now has to consider the stub.
