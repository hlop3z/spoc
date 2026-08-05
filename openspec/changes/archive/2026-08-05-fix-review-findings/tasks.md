# Tasks — fix-review-findings

## 1. Kernel: identity and declaration

- [x] 1.1 Rename `Identifier` field `name` → `object_name` in `core/identity.py`; update every use in kernel, tests, and docs (**BREAKING**, no alias)
- [x] 1.2 `core/exceptions.py` / `core/declaration.py`: make `InvalidSegmentError` remediation match the path taken — derived-name failures state the name was derived and name the intrinsic source
- [x] 1.3 `framework.py.__init__`: raise on duplicate kind declarations, naming the duplicated kind
- [x] 1.4 `core/declaration.py`: wrap the mark write so an unmarkable object (slots, builtins) raises a kernel error naming the object and the constraint
- [x] 1.5 `core/declaration.py` discover: stop silently skipping already-identified instances — a second location whose derived identity differs raises the identity-divergence error naming both identities; classes/functions keep the `__module__` re-export skip
- [x] 1.6 `core/registry.py`: exempt runtime-interned immutable values from `id()`-keyed divergence tracking so equal primitives register under distinct identifiers
- [x] 1.7 `core/loader.py`: raise on re-registration of a loaded module name with different dependency edges (internal hardening, no spec delta)
- [x] 1.8 `core/__init__.py`: add the docstring the top-level module advertises

## 2. Kernel: lifecycle

- [x] 2.1 `framework.py`: record the transition-owning thread; a lifecycle call from within an in-flight transition raises `SpocError` naming the reentrant call (sync path — async already fails loudly); clear the marker in `_reset`
- [x] 2.2 `core/loader.py`: fire the kind shutdown hook during rollback for modules whose startup hook ran but whose `initialize()` failed — hook pairing symmetric under failed boot (sync and async paths)
- [x] 2.3 `framework.py._register_plugins`: refuse plugin groups naming a metadata-contract kind with an error stating configured registrations cannot satisfy a metadata contract
- [x] 2.4 Update `Framework` concurrency-contract docstring (reentrancy) and `KindSpec` hook docstring (per-(kind, namespace)-module dispatch; plugin-only kinds get no hooks)

## 3. Kernel: configuration

- [x] 3.1 `core/config.py`: enforce the closed `[spoc]` key set — unknown keys fail with `ConfigurationError` naming the key and the valid set; fix the "four keys" docstring
- [x] 3.2 `core/config.py`: deep-copy `SPOC_DEFAULTS`/`DEFAULT_MODES` before merge so loaded config never aliases module-level defaults
- [x] 3.3 `core/config.py`: map `PermissionError`/`OSError` in `read_toml` into `ConfigurationError`
- [x] 3.4 `core/config.py`: gate the missing-`spoc.toml` warning on `echo`, same as env-file warnings

## 4. Formats

- [x] 4.1 `formats/operations.py` collect: skip dot-prefixed files/directories by default, add `ignore=(pattern, ...)` parameter, report skips before key derivation; collected keys stay loud
- [x] 4.2 `formats/operations.py` write: create parent directories
- [x] 4.3 `formats/access.py`: wrap syntactically invalid pointer/query errors from the engine into the `FormatError` family, naming the address/query
- [x] 4.4 `formats/codecs.py`: wrap encoder-side failures (json `TypeError`, tomli_w, ruamel representer) into the `FormatError` family naming format and offending value
- [x] 4.5 `formats/codecs.py` CSV reader: reject short rows naming the row, symmetric with the overflow check
- [x] 4.6 Add drift-guard test: the overridden extension attribute set equals the installed `python-jsonpath` extension surface, so an upgrade that would widen accepted syntax fails the suite

## 5. Scaffold

- [x] 5.1 `scaffold/core.py` `_reject_escape`: reject backslash traversal, absolute, and drive-/root-qualified paths in the pure validation layer; keep the sink barrier as defense in depth
- [x] 5.2 `scaffold/sources.py`: resolve entry-point targets that are importable packages via `importlib.resources.files()` + `as_file()`, honoring the documented contract
- [x] 5.3 `scaffold/sources.py`: replace `Path(str(resources.files(...)))` for the built-in set with the `as_file` context-managed form so non-directory installs work

## 6. Tests

- [x] 6.1 Framework-level `Config` coverage: `fw.config` population, `echo` flag behavior, env loading through `start`, `default.toml` fallback regardless of echo
- [x] 6.2 Scaffold CLI argv layer: `main(["init", ...])` happy path, `--kinds/--app/--path/--template` parsing, non-empty target exit behavior
- [x] 6.3 Circular-dependency test through the public `Framework`/`KindSpec` constructor (drop reliance on hand-wired private loader state where possible)
- [x] 6.4 Tests for every new behavior in groups 1–5, one per spec scenario added/modified (reentrancy, duplicate kind, instance divergence, interned values, closed key set, default isolation, hidden-dir skip + ignore patterns, short CSV rows, error containment, backslash/drive escapes, package template sets, hook pairing under failed boot, plugin/metadata refusal)
- [x] 6.5 Delete `tests/TEST.md`

## 7. Docs and repo hygiene

- [x] 7.1 Docs: lifecycle page states sync discovery on `astart` and the per-module hook dispatch rule (plugin-only kinds); plugins page documents the metadata-contract refusal; data-formats page documents hidden/ignore skip behavior and CSV short-row refusal
- [x] 7.2 Fix `quick-start.md` internal inconsistency (`apps.core` generator output vs `apps/blog` layout section)
- [x] 7.3 `Taskfile.yml`: add `pytest-cov`/`pytest-watch` to a dev dependency group or delete `test:cov`/`dev:watch`; deduplicate `version:bump:*` into one parameterized task
- [x] 7.4 `CHANGELOG.md`: document all behavior changes under 0.5.0 (including the `Identifier.object_name` rename); fix the `[0.5.0]` compare link
- [x] 7.5 Regenerate `HANDOFF.md` via /ai:handoff (current post-reunification state); confirm `tests/TEST.md` removal
- [x] 7.6 Run `.canon/checks.md` validation suite; report anything unverifiable
