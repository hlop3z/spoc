## Why

The kernel spends 1,823 lines doing one job — declare kinds, import apps, register
components — across nine modules whose boundaries do not match that job. The registry is
owned by the module importer, so the loader must know what a kind is; the declared kind set
is validated and stored in three places and re-checked from five; a regex pattern engine
exists to answer a question the discovery step already computes; and roughly a third of the
file volume is per-function prose restating information the type annotations already carry.

Two deferred API items have been waiting on this. Per-kind strict/loose optionality and
typed per-kind component metadata are both currently impossible to add cleanly: each would
have to be threaded as a new parameter through five layers, because a kind is a bare string
with its attributes scattered across parallel dictionaries. Once a kind is one declared
object, both become fields rather than plumbing — which is the argument for doing the
collapse instead of the two narrow changes.

SPOC has no users. There is no installed base to protect, so this is the last moment when
the shape can be fixed without a migration cost.

## What Changes

- **Redraw the kernel's boundaries to match its four jobs** — identity, declaration, boot,
  and storage — so the registry is no longer owned by the module loader and the loader no
  longer knows what a kind is.
- **A kind becomes one declared object instead of a bare string.** Its dependencies,
  optionality, metadata contract, and lifecycle hooks stop living in parallel dictionaries
  keyed by kind name.
- **BREAKING — per-kind optionality replaces the global strict/loose switch.** A framework
  can declare more kinds than any single app uses without forcing every missing module in
  the project to be tolerated. Today's whole-framework switch is removed, not deprecated.
- **BREAKING — component metadata becomes typed and kind-declared.** The untyped
  configuration dictionary carried on every record is removed; a kind states what metadata
  its components carry, and registration is checked against it.
- **BREAKING — the public surface shrinks to what a framework author actually needs.**
  Module-cache manipulation, case-conversion utilities beyond the one the kernel uses, and
  internal declaration machinery stop being exported.
- **Remove capability that no caller exercises**: constructor options that are stored and
  never read, empty subclass extension points in a design that composes rather than
  subclasses, and cache/unload operations reachable only from their own tests.
- **Documentation policy: module docstrings are for humans, object docstrings are for
  machines.** Module-level prose explaining why a module exists is kept and curated. On
  functions, classes, and methods, hand-written parameter, return, and raises blocks are
  removed — signatures and type annotations carry that, and the failure contracts are
  already stated in `specs/`. A one-line summary survives only where a symbol is published
  in the API reference and its name plus types do not already say it.
- **The published API reference is updated in the same change set**, since it renders from
  these docstrings and its build fails on any symbol that no longer exists.

Success is measured in lines: the kernel goes from 1,823 to roughly 810 (~55%), and
`src/spoc` from 2,463 to roughly 1,390 (~41%). The scaffolder is deliberately untouched.

## Capabilities

### New Capabilities

None. Every behavior change lands in an existing capability.

### Modified Capabilities

- `framework-declaration`: a declared kind gains per-kind attributes — whether modules of
  that kind are required or optional, and what metadata its components carry — rather than
  being a bare name whose attributes live in separate structures.
- `framework-lifecycle`: a missing module is resolved against the declaring kind's own
  optionality rather than one framework-wide setting. A missing required module fails start;
  a missing optional one is skipped.
- `component-registry`: records carry metadata conforming to the declaring kind's stated
  contract, replacing the requirement that they carry an arbitrary untyped configuration
  dictionary supplied at registration.

## Impact

**Critical concern requiring a build-vs-adopt decision before implementation** (`/ai:decide`):

- *Declarative configuration validation.* The kernel currently hand-rolls a recursive
  type-checking validator for its configuration file. Standards-first says adopt a
  recognized schema standard; the package's zero-runtime-dependency property — verified in
  the built wheel — says every candidate has a cost. This is a genuine tension and the
  concrete choice is deferred, not assumed.

**Affected code**: the whole kernel — module loading, the framework object, the declaration
layer, the registry, discovery, the error family, identity, configuration loading, case
conversion, and the package's export list. `src/spoc/scaffold/` is explicitly out of scope
and is a separate subject.

**Affected APIs**: every removal above is breaking. Acceptable without a migration path
because the package has no users.

**Affected docs**: the published API reference renders from the docstrings this change
removes and references symbols this change deletes. Architecture diagrams describing the
kernel's current shape stop being accurate the moment the boundaries move.

**Affected tests**: tests covering removed API are removed with it. Coverage of behavior
that survives is preserved; no test is deleted to reduce a line count.

**Deferred, not foreclosed**: whether module lifecycle, the plugin table, and the
environment cascade belong in the kernel at all is a capability question, deliberately left
for a later change once this structural one has landed.
