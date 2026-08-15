# Design — cache derived results computed from immutable inputs

## Context

Three sites re-derive a result whose inputs cannot have changed between derivations:

- `core/registry.py` — `all()`, `by_kind()`, `by_namespace()` (and `__iter__`, which routes
  through `all()`) re-sort on every call. The store is written only by `_admit`, which the
  class documents as **the only mutator of registry state**, so between admissions every
  sort recomputes a constant.
- `formats/core.py` — `FormatRegistry.function` caches successful resolutions in
  `self._resolved` but not failures. A missing extra re-runs the factory's import on every
  probe, and Python does not cache failed imports, so each retry re-walks every `sys.path`
  finder. `supported()` probes both directions of every codec, multiplying this.
- `stubs/manifest.py` — `_entries` calls `reference_for` once per registry *entry*;
  `inspect.signature` + `typing.get_type_hints` (which evals stringified annotations) are
  recomputed even when several identifiers name one object.

All three fixes are pure-core, stdlib-only, and invisible at every public surface except the
one behavior change the proposal calls out (mid-process extra installation).

## Goals / Non-Goals

**Goals:**

- Ordered enumeration derived at most once per registry mutation.
- Codec availability settled on first probe, for failure as well as success.
- One type-reference extraction per distinct object during stub description.
- No public API signature or return-type changes.

**Non-Goals:**

- The audit's nanosecond-tier tidies in untouched files (`navigation.py` repr,
  `config.py` double deep-copy, `scaffold/core.py` set hoisting, `alias_for` memo).
- Moving `_kind_ranks` to `Framework.__init__` — it changes *when* kind-cycle errors are
  raised, which is a lifecycle-spec question, not a caching one.
- Caching `Loader.ordered()` across boot phases — each phase deliberately reads one
  self-consistent order; imports dominate boot by orders of magnitude.

## Decisions

### D1 — Registry: one ordered-view cache, invalidated at the single mutator

A private `dict` keyed by facet — the whole store, one kind, or one namespace — holding the
sorted result, populated on first read under the existing lock and **cleared unconditionally
in `_admit`**. Anchoring invalidation in `_admit` inherits the class's central invariant
(every write goes through it, and a test fails if a second writer appears), so the cache
cannot go stale without that invariant breaking first.

Reads return `list(cached)` — an O(n) copy replaces the O(n log n) sort, and callers keep
receiving a fresh mutable list, so no signature or aliasing change is observable.

*Alternatives considered:* maintaining sorted insertion order (`bisect` at `_admit`) — more
code on the write path for no read-side gain over a cache; returning the cached list
directly — aliases internal state to callers; a tuple return — a public API change the
proposal excludes.

### D2 — Codecs: record the failure, raise it fresh

`_resolved` keeps holding successes. Failures are recorded in a parallel map keyed the same
way (`(name, direction)` → the context and extra needed to build `MissingDependencyError`),
written when the factory's import fails. A hit raises a **newly constructed**
`MissingDependencyError` rather than re-raising a stored exception object, so tracebacks
stay clean and no exception instance is shared across call sites.

`UnsupportedDirectionError` is *not* cached: it costs a dict lookup, involves no import, and
caching it would add a second code path for nothing.

A short comment at the failure-cache write records the deliberate trade the spec now pins:
a mid-process `pip install` of an extra is not observed until a new process.

*Alternatives considered:* storing exception instances in `_resolved` behind `isinstance`
checks — muddies a map that currently holds only callables and mutates shared exception
state on each re-raise; `functools.cache` on `function` — cannot express "cache the raise"
without the same wrapper logic, and the registry is instance-scoped.

### D3 — Stubs: per-object memo inside `_entries` — **withdrawn during implementation**

The plan was a local `dict[int, TypeRef]` keyed by `id(obj)`, consulted before
`reference_for`. It was implemented, then reverted: the saving it targets is unreachable.

A memo only pays when one object appears under several identifiers, and `Registry.add`
forbids precisely that for every object whose extraction is expensive. A callable or a class
is *tracked* (it is not in `_SHARED_VALUE_TYPES`), so a second identifier raises
`IdentityDivergenceError` — verified directly against the registry. What remains registrable
under several identifiers is the shared value types (`int`, `str`, `tuple`, `None`, …), and
those take `reference_for`'s `value` branch: `_named_type(type(obj))`, a frozenset membership
test and two `getattr`s. The expensive branch — `inspect.signature` plus `get_type_hints` —
is reachable only through `_callable_reference`, which only tracked objects reach.

So the memo would cache the cheap answer and could never cache the dear one. The audit
finding it came from assumed the two modules were independent; the registry's identity
invariant already closes the case.

Recorded as a comment in `_entries` rather than only here, because the reasoning spans two
modules and is not derivable from either alone — the next reader of that loop would otherwise
re-propose it.

### Build-vs-adopt

No critical concern in this change reaches outside the process: all three mechanisms are a
stdlib `dict` guarding work the core already does. There is no external system, dependency,
or vendor choice to gate through `/ai:decide`, and nothing to rent or adopt beyond the
standard library already in use.

## Risks / Trade-offs

- [Registry cache staleness if a second mutator ever appears] → invalidation lives in
  `_admit`, whose only-mutator invariant an existing suite test already enforces; a new
  writer fails that test before it can strand the cache.
- [Mid-process extra installation no longer picked up] → specced explicitly (delta to
  `format-codecs`) with a scenario, and commented at the cache site; a restart observes the
  install, matching every other import in the process.
- [Cache key growth] → `by_kind`/`by_namespace` accept any string, so caching *misses* would
  let a caller grow the dict without registering anything. Only non-empty facets are kept,
  which bounds the cache by what is actually registered rather than by caller discipline; a
  miss re-derives through a handful of failed dict lookups, with no records to order. Codec
  failure keys are bounded by codecs × two directions.
- [`id()` reuse in the stubs memo] → impossible while the memo is alive: the `objects` dict
  in the same scope holds strong references to every keyed object.

## Migration Plan

No migration. Greenfield project, no back-compat surface; the one behavior change ships
with its spec delta in the same change set.

## Open Questions

None.
