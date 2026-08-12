## Why

The ordering guarantee is stated weakly and implemented strongly, and the gap is invisible
from either side.

`openspec/specs/framework-declaration/spec.md` promises that modules of kind `models` are
loaded and initialized before modules of kind `views` **in every app** — a per-app chain,
which permits one app's `views` to load before another app's `models`. The implementation
delivers something stronger: every app's `models` module loads and initializes before any
app's `views` module. Measured by running the graph `Framework._register_apps` builds
through `graphlib`, for two apps and three chained kinds:

```
apps.blog.models  apps.shop.models      ← level 0
apps.blog.views   apps.shop.views       ← level 1
apps.blog.urls    apps.shop.urls        ← level 2
```

`static_order()` yields level by level, and because `_register_apps` gives every app an
identical kind graph, `X.views` sits at the same depth for every `X`. The barrier is real,
and it is a side effect of two facts that no document connects.

The strong property is the one that matters. `Loader.initialize` walks `ordered()`, firing
each kind's startup hook per module in load order, so a `views` hook that binds routes
against every registered model would see a half-built world if another app's `models` hook
had not yet run. Today it cannot. Nothing says so, and no test holds it.

Two forces make this urgent rather than tidy. The pre-stable allowance ends at the first
stable major release and cannot be extended (`openspec/specs/release-policy/spec.md`), so
after that release the behavior binds whether or not it was ever specified — an unspecified
promise that consumers depend on is API that nobody decided. And Django, whose app model
this project otherwise follows, paid exactly this bill: version 1.7 had to introduce
`AppConfig` and a two-phase `populate()` nine years in, because the original design left
load timing implicit and an ecosystem had already built on the accident.

## What Changes

- The cross-app load-phase barrier becomes a **stated, tested invariant**: for any two
  installed apps and any two kinds where one depends on the other, no app's dependent
  module loads or initializes before any app's depended-on module.
- The load order becomes a **stated total order** — kind depth first, app declaration order
  as tiebreak — rather than a property emerging from a library's batching behaviour. The
  observable behaviour is unchanged; what changes is that it is a contract instead of a
  coincidence.
- The `[spoc.apps]` declaration order becomes the stated tiebreak among modules of one
  kind, which it already is in practice.
- A cross-phase dependency inversion is **refused by construction**: no declaration may
  express "this app's `urls` before that app's `models`", because that is the only shape
  that can break the barrier.
- **No new configuration key and no new public name.** This change is specification and
  tests, plus whatever is needed in the loader to own the ordering rule rather than inherit
  it from `graphlib`'s batching.

## Capabilities

### New Capabilities

<!-- None. This states a guarantee the implementation already provides. -->

### Modified Capabilities

- `framework-declaration`: the inter-kind ordering scenario is strengthened from a per-app
  chain to a cross-app barrier, so the declaration's meaning is stated once and completely.
- `framework-lifecycle`: gains the load-order requirement — the total order, its tiebreak,
  the barrier, and the refusal of any cross-phase inversion.

## Impact

- `src/spoc/core/loader.py` — `ordered()` delegates the entire order to
  `graphlib.TopologicalSorter.static_order()`. Whether it continues to is Decision 1 in
  `design.md`; either way its contract stops being a library's and becomes ours.
- `src/spoc/framework.py` — `_register_apps` is what makes every app's kind graph
  identical, which is the mechanism the barrier currently rests on. It is the site a future
  per-app kind subset would change, and therefore the site the new tests protect.
- `tests/` — coverage pinning the barrier across at least two apps and two kinds, pinning
  the declaration-order tiebreak, and pinning that hook firing order follows the same rule
  as module load order.
- `docs/architecture/kernel.md` — the invariants list gains the ordering contract; Rule 1
  makes the diagram describe what is.
- No new dependencies, no configuration change, no public API addition.
