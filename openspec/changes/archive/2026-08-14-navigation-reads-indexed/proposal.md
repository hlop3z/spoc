# Reading one facet costs the facet, not the registry

## Why

The README states that `resolve("models:blog.post")` and `objects.models.blog.post`
yield the identical record either way — and they do, but at wildly different cost.
Measured at 50,000 components: `resolve` answers in 0.35 µs (one dict hit), while one
navigation walk takes 10.6 ms — a 30,000× gap. Each navigation step calls
`registry.all()`, which snapshots and *sorts the entire registry* before filtering to
one kind or namespace; `_namespaces()` then discards the sort into a set. A user who
takes the documented equivalence at face value and navigates in a request loop gets a
full-registry scan per request. The registry is add-only — nothing is ever removed —
so a facet index maintained at registration has no invalidation problem at all: the
scan is not a trade-off being made, it is work being wasted.

## What Changes

- The registry maintains a facet index (kind → namespace → object name → record),
  updated inside the same locked region that admits a registration. Navigation steps
  and faceted reads answer from the index instead of scanning and sorting the whole
  store.
- Navigation's per-step cost becomes independent of how many *unrelated* components
  are registered. Behavior is unchanged: same records, same errors, same candidate
  lists in failures, same deterministic enumeration order.
- A scale test pins the property — the cost of reading one facet must not grow in
  proportion to the size of the rest of the registry — so a future edit cannot
  quietly reintroduce the scan.
- No public API changes. The index is internal state of `Registry`; the stability
  contract already excludes internal attributes of public types.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `component-registry`: the enumeration requirement gains the cost contract — reading
  one facet of the registry must not cost proportional to the whole registry, and
  registration remains the only writer, so the reads need no coordination beyond the
  existing atomicity guarantee.

## Critical concerns

- **Index/store coherence under concurrency** (correctness): the index must never
  disagree with the store — a record visible through one and not the other would
  violate the atomic-registration requirement. Realized inside the existing lock;
  whether any adopted structure is warranted is settled in design (it is not — the
  index is two nested dicts of the standard library).

## Impact

- `src/spoc/core/registry.py` — facet index in `add()`; faceted readers answer from it.
- `src/spoc/core/navigation.py` — steps read the index views instead of `all()`.
- `tests/` — the scale property; existing registry/navigation suites unchanged and
  green (behavior is identical).
- No dependency, configuration, or documentation-surface changes.
