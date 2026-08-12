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
