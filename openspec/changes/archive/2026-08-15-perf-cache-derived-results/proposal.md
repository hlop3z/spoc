# Cache derived results computed from immutable inputs

## Why

A whole-package algorithmic audit (2026-08-14) found three places that re-derive the same
result from inputs that cannot have changed: registry enumeration re-sorts a frozen store on
every read, codec resolution re-attempts a failed optional import on every probe (and Python
does not cache failed imports, so each retry re-walks all path finders), and stub generation
re-extracts type hints once per registry entry even when several identifiers name one object.
None is a measured hotspot today; all three are one-dict fixes that stop the cost from scaling
with future callers instead of with actual change.

## What Changes

- Registry enumeration (`all`, `by_kind`, `by_namespace`, iteration) derives its ordered view
  once per mutation instead of once per read. Determinism and ordering are unchanged.
- Codec resolution remembers failure as well as success: the first probe of a format whose
  optional dependency is missing settles the outcome for the process, and repeated
  `supported()` calls stop re-running import machinery. **Behavior change**: installing an
  extra mid-process is no longer picked up — a restart is required. (Today's pickup is
  accidental, unspecified, and only reachable by mutating the environment under a running
  process.)
- ~~Stub description extracts each component object's type reference once per object.~~
  **Withdrawn during implementation**: the registry already refuses a second identifier for
  every object whose extraction is expensive, so the saving is unreachable. See design D3 —
  the reasoning is now a comment in `_entries` so it is not rediscovered as a finding.

Deliberately out of scope: the audit's nanosecond-tier tidies (repr sorting, duplicate
deep-copies, per-file set rebuilds) — they live in files this change does not touch and are
not worth their own review surface.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `component-registry`: the enumeration requirement gains a cost-model clause — repeated
  reads of an unchanged registry do not re-derive order (the existing "reading one facet does
  not pay for the rest" clause already sets this precedent).
- `format-codecs`: the missing-optional-dependency requirement gains a stability clause — the
  outcome of probing a format is settled per process, and enumerating supported formats does
  not repeatedly re-pay the failed-import cost.

## Impact

- `src/spoc/core/registry.py` — cached sorted enumeration, invalidated at the single mutator.
- `src/spoc/formats/core.py` — negative caching in codec resolution and availability probing.
- `src/spoc/stubs/manifest.py` — docstring only: why per-object memoization is not done.
- Tests for the two specced behaviors, counting derivations rather than timing them.
- `tests/test_registry.py` — the one-writer guard becomes per-attribute, so authoritative
  state stays pinned to `_admit` while the derived cache declares its own writer.
- No public API changes. One observable behavior change (mid-process extra installation),
  called out above.
