# Fix 2026-08-05 review findings

## Why

A full-source review (2026-08-05) found a recurring pattern: **documented contracts stronger
than the code**. Several gaps would produce confused issue reports in early real-world use —
a sync-path deadlock on reentrant lifecycle calls, silent misregistration of imported
instances, a plugin dead-end on metadata kinds, and an unignorable hard failure in
`formats.collect`. None are structural; fixing them now, before the 0.5.0 tag lands,
closes the gap between what the docs promise and what the code does.

## What Changes

### Kernel — contract enforcement

- Reentrant lifecycle calls from hooks/callbacks on the sync path fail loudly instead of
  deadlocking on the non-reentrant transition lock.
- Discovery's "imported, declared elsewhere" filter covers marked **instances**, not just
  classes and functions — an instance re-exported by another app can no longer silently
  register under the importing app's namespace.
- Duplicate kind declarations in the `Framework` constructor raise instead of silently
  last-winning.
- A kind that declares a metadata contract refuses plugin population with a message that
  says why (plugins cannot carry metadata), instead of a generic `MetadataContractError`.
- The `[spoc]` table's closed key set is enforced: unknown keys are rejected with the
  valid set named, instead of merging silently.
- Configuration defaults are isolated per framework instance — mutating
  `framework.config.project` can no longer corrupt process-wide defaults.
- Hook pairing is symmetric under partial boot: a module whose `initialize()` raises still
  gets its kind's shutdown hook during rollback.
- Loader re-registration of an already-loaded module name with different dependency edges
  raises instead of silently ignoring the new edges.
- Registry identity divergence detection no longer false-positives on interned values
  (equal small ints / interned strings from distinct plugin URIs).
- Marking a slot-restricted or otherwise unmarkable object raises a kernel error naming
  the constraint, not a raw `AttributeError`.
- `InvalidSegmentError` remediation text matches the path taken (derived vs stated name).
- `read_toml` maps `PermissionError`/`OSError` into the `ConfigurationError` family;
  missing-`spoc.toml` warning respects the same `echo` gating as env-file warnings.
- `Identifier` field renamed `name` → `object_name` to match the grammar vocabulary
  everywhere it is defined. **BREAKING** (greenfield; no compat shim per standing mandate).
- `spoc.core.__init__` gains the docstring the top-level module advertises.

### Formats — failure containment

- `collect` gains an ignore mechanism (hidden directories skipped by default; explicit
  ignore patterns) so one stray `.cache/foo.json` no longer kills the whole collection.
- Every failure the formats surface produces is contained in the `FormatError` family:
  invalid pointers/queries and encoder-side failures no longer escape as third-party or
  raw exceptions.
- CSV decoding is symmetric: short rows are rejected like overflow rows (no silent `None`
  padding that violates the declared `list[dict[str, str]]` model).
- `write` creates parent directories for a fresh output path.
- RFC 9535 extension suppression is drift-guarded: a test pins the overridden attribute
  names against the installed `python-jsonpath` so a lib upgrade cannot silently re-enable
  non-RFC syntax.

### Scaffold — extension points honored

- The entry-point contract "directory path **or importable package**" is implemented
  (importable-package targets resolve via `importlib.resources`, not `Path(str(module))`).
- Built-in template resolution uses `importlib.resources` correctly (`as_file`), so
  non-directory installations work.
- Pure-layer path-escape rejection covers backslash traversal and Windows drive-letter
  targets, matching the comment that claims the pure layer holds this guarantee.

### Lifecycle documentation

- Plugin-registered components' hook behavior is documented truthfully (per-(kind,
  namespace)-module dispatch; plugin-only kinds receive no hooks), and `astart`'s
  synchronous discovery I/O is stated in the public docs.

### Hygiene

- Framework-level tests for `Config`, the `echo` flag, and env loading through `start`.
- Scaffold CLI argv layer covered (happy path, flag parsing, non-empty target).
- Framework-level circular-dependency test through the public constructor.
- Taskfile: `test:cov` and `dev:watch` tools declared in a dependency group, or the tasks
  removed; `version:bump:*` deduplicated.
- CHANGELOG `[0.5.0]` compare link fixed to a real target.
- Stale `HANDOFF.md` regenerated post-reunification; `tests/TEST.md` deleted.

## Capabilities

### New Capabilities

None — every fix lands inside an existing capability.

### Modified Capabilities

- `framework-lifecycle`: reentrant transition calls fail loudly; hook pairing symmetric
  under failed boot; plugin/hook dispatch and `astart` I/O documented truthfully. (The
  loader re-registration hardening is internal-only — unreachable via the public API —
  so it lands as code + test without a spec delta.)
- `framework-declaration`: imported-instance filter; duplicate kind declaration raises;
  unmarkable objects raise a kernel error; metadata-kind plugin refusal message.
- `project-configuration`: closed `[spoc]` key set enforced; per-instance default
  isolation; `ConfigurationError` containment for all file errors; consistent `echo`
  gating.
- `component-registry`: identity divergence check robust to interned values.
- `object-identity`: `Identifier.name` → `Identifier.object_name` (**BREAKING**).
- `data-collection`: ignore mechanism; hidden directories skipped by default; `write`
  creates parents.
- `data-access`: `FormatError`-family containment for pointer/query failures; extension
  suppression drift guard.
- `format-codecs`: CSV short-row rejection; encoder-side failure containment.
- `project-scaffolding`: pure-layer escape rejection covers backslash/drive-letter paths;
  CLI argv layer specified as tested surface.
- `scaffold-templates`: importable-package entry points resolve; resource access works on
  non-directory installs.

## Impact

- **Code**: `src/spoc/framework.py`, `src/spoc/core/{declaration,loader,registry,config,identity,exceptions,__init__}.py`, `src/spoc/formats/{operations,access,codecs}.py`, `src/spoc/scaffold/{core,sources}.py`.
- **Tests**: new coverage in `tests/test_framework.py`, `test_config.py`, `test_formats.py`, `test_scaffold.py`, `test_loader.py`, `test_registry.py`; delete `tests/TEST.md`.
- **API**: one breaking rename (`Identifier.name` → `Identifier.object_name`); everything
  else tightens failure behavior only (silent-wrong → loud error, or contained error).
- **Docs**: lifecycle/plugins pages updated where behavior is clarified; CHANGELOG entry.
- **Repo**: `Taskfile.yml`, `CHANGELOG.md`, `HANDOFF.md`, `tests/TEST.md`.
- **Dependencies**: none added (`dependencies = []` invariant untouched).
