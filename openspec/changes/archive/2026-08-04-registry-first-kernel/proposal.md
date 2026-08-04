# Registry-First Kernel

## Why

SPOC is being adopted as the studio's runtime kernel — the layer that manages internal
resources and application objects underneath any HTTP framework (FastAPI, Robyn, …). But
its component registry is currently scaffolding, not product: the runtime path silently
drops objects on a kind/module-name mismatch, carries two competing identifier grammars
(neither Rule 11-compliant), derives instance identity from call-stack inspection, and
resolves lookups by returning `None` with no indication of what failed. SPOC is on PyPI
with no users, so breaking changes are free — the cheapest moment to fix identity and
resolution is now, before any consumer exists.

## What Changes

- **BREAKING** — One identifier grammar: `kind:namespace.object_name`, lowercase
  snake_case, validated at registration. Registration **rejects** non-conforming names
  with an error naming the offending segment; it never normalizes. Both existing
  grammars (`app_object` builder URIs and `app.Object` runtime keys) are removed.
- **BREAKING** — Flat registry as the only component store: one enumerable set of typed
  component records with `kind` / `namespace` / `name` facets, replacing the
  dict-of-dicts keyed by module name and the silent `type == module` filter (a mismatch
  becomes a startup error naming the file and object).
- **BREAKING** — Precise resolution: `resolve(identifier)` fails per segment with an
  error naming what didn't resolve, replacing `get_component`'s silent `None` returns.
  No `.operation` segment and no invocation API — the kernel describes, it never
  executes user code beyond lifecycle hooks.
- **BREAKING** — Closed kind set per project: the schema's declared modules define the
  kinds; registering an unknown kind is an error, not an implicit type creation.
- **BREAKING** — Explicit identity only: instance registration requires an explicit
  name; call-stack walking (`_locate_obj`) and caller-class mutation for hashability are
  removed.
- **BREAKING** — De-globalized composition: the importer and its hooks become instance
  state owned by the framework object; the singleton metaclass and class-level hook
  registry are removed, so two frameworks can coexist in one process and tests are
  isolated.
- **BREAKING** — Scope-line deletions: worker/execution primitives (`workers.py`), the
  parallel tool-introspection registry (`tools.py`), and trivial shims (`types.py`,
  `utils.py`, `core/singleton.py`) are deleted. Execution machinery is out of kernel
  scope; the studio's event/execution engine registers on the kernel as an app.
- Docs shrink in the same change set (Rule 8): pages teaching the dead URI grammar,
  workers, and tools are deleted or rewritten against the new registry; a canonical
  architecture diagram is added under `docs/architecture/`.
- Kept as-is (this is the adopted value): app discovery, dependency-ordered module
  loading, lifecycle hooks with reverse-order teardown, TOML configuration, the
  development→staging→production mode cascade, plugin loading, and `case_style` as a
  projection utility.

## Capabilities

### New Capabilities

- `object-identity`: the identifier grammar — `kind:namespace.object_name` — its
  character rules, its validation-at-registration contract (reject, never normalize),
  and the closed per-project kind set. Correctness-critical: identifiers are contracts;
  a rename is a breaking change.
- `component-registry`: the single flat store of component records — registration,
  faceted enumeration (by kind, namespace, or both), and the metadata each record
  carries so that external surfaces (HTTP routes, schemas, docs) can be projected purely
  by reading it. Correctness-critical: silent drop of a declared component is a defect.
- `component-resolution`: lookup of a registered object by identifier, failing with a
  precise per-segment error; resolution never invokes what it returns.

### Modified Capabilities

<!-- none — openspec/specs/ is empty; there are no existing main specs to modify -->

## Impact

- **Code**: `src/spoc/core/importer.py` (registration path and component store),
  `src/spoc/components.py` (grammar, validation, record building; deletions),
  `src/spoc/framework.py` (resolution API, composition-root ownership). Deleted:
  `src/spoc/workers.py`, `src/spoc/tools.py`, `src/spoc/types.py`, `src/spoc/utils.py`,
  `src/spoc/core/singleton.py`. Net package size shrinks (~2,700 → ~2,000 LOC).
- **Public API**: `spoc.__init__` exports shrink; every removal is breaking by design
  (greenfield licence — no deprecation shims, no compat views).
- **Dependencies**: none added; the zero-runtime-dependency invariant is explicit and
  preserved.
- **Tests**: `tests/test_workers.py`, `tests/test_tools.py`, `tests/test_singleton.py`
  are deleted with their modules; component/importer/framework tests are rewritten
  against the new grammar and registry.
- **Docs**: `docs/docs/advanced/workers.md`, `docs/docs/api/workers.md`,
  `docs/docs/api/tools.md` deleted; `components`, `framework`, `importer`, quick-start,
  and example pages rewritten; `README.md` repositioned (kernel under any HTTP surface,
  not an app framework).
- **Definition of done**: an example app generates its HTTP routes purely by
  enumerating the registry through the public API, importing no SPOC internals. When
  that works and identifiers validate per Rule 11, the kernel is feature-complete.
