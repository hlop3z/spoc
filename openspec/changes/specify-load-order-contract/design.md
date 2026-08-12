## Context

Three facts, each documented somewhere, none connected to the others.

**One.** `Framework._register_apps` registers every declared kind for every declared app,
wiring dependency edges only *within* an app:

```python
dependencies=tuple(f"{entry.path}.{d}" for d in spec.depends_on)
```

So the module graph is a disjoint union of identical chains, one per app.

**Two.** `Loader.ordered()` returns `graphlib.TopologicalSorter(...).static_order()`, which
is specified as repeated `get_ready()` / `done()` — that is, level order. A disjoint union
of identical chains therefore emits every app's kind-*n* module before any app's
kind-*n+1* module.

**Three.** `Loader.initialize` walks `ordered()` and fires each kind's `on_startup` hook per
module, so load order is directly observable through hooks and through a module's own
`initialize()`.

Together these produce a cross-app phase barrier that the specification does not claim.
`framework-declaration/spec.md` says only "in every app", which is the weaker per-app
reading. Measured on the current build with apps `blog` and `shop` and kinds
`models → views → urls`, the order is `blog.models, shop.models, blog.views, shop.views,
blog.urls, shop.urls`.

Worth stating plainly what does *not* depend on this. Python's own import system resolves
import-time coupling between app modules, and SPOC already separates marking from
registering — decorators set an attribute, `discover()` populates the registry later in
loader order — so import order does not affect registry contents. `Registry.by_kind` sorts
by canonical identifier, so load order does not affect what surfaces enumerate either. The
barrier's entire observable surface is hook firing and module `initialize()`. That is a
small surface, and a real one: it is where a kind's components are handed to code that acts
on them.

## Goals / Non-Goals

**Goals:**

- State the cross-app barrier as a requirement, in terms a reader can check.
- State the total order and its tiebreak, so two starts of one project are identical and a
  reordering of `[spoc.apps]` has a defined effect.
- Own the ordering rule rather than inherit it from a library's batching behaviour.
- Make a cross-phase inversion inexpressible, since that is the only way to break the
  barrier.
- Pin all of it with tests, so a future change to `_register_apps` fails here rather than
  in a consumer's startup hook.

**Non-Goals:**

- Per-app dependency declaration. Refused for now; see Decision 4 and the corresponding
  entry in `DECISIONS.md`.
- Changing enumeration order. `by_kind` stays canonical-identifier ordered; see Decision 3.
- Per-app kind subsets (an app declaring it participates in only some kinds). That feature
  is what would break the barrier, and this change exists partly to make that constraint
  visible before anyone builds it.
- A graph abstraction of our own. The ordering key is a tuple over data the kernel already
  holds; anything that would need general graph algorithms is a signal to adopt a library,
  not to grow this one.
- Any change to observable behaviour. If the implementation's order changes at all, this
  change is wrong.

## Decisions

### Decision 1: Own the order as an explicit key, keep `graphlib` for cycle detection

Compute each module's position from a tuple — `(kind_depth, app_index)` — where
`kind_depth` is the longest-path depth in the `KindSpec` dependency graph and `app_index`
is the position of the app in the effective `[spoc.apps]` list. Retain
`graphlib.TopologicalSorter` for what it is uniquely good at: detecting cycles in the kind
graph and raising `CircularDependencyError`.

The tuple key is sound because every dependency edge runs from a lower `kind_depth` to a
higher one — that is what `depends_on` means — so sorting by depth satisfies every edge,
and `app_index` breaks ties deterministically without being able to violate one.

This is the shape Odoo arrived at independently: its module graph sorts by
`(phase, depth, order_name)`. Two systems reaching the same key is weak evidence, but it is
evidence.

**Alternatives considered.** *Keep `static_order()` and document the level-order behaviour*
— cheapest, and not wrong, but it makes a library's iteration strategy load-bearing for our
guarantee, and the guarantee then holds for a reason no reader of our code can see.
*Synthetic barrier nodes* — insert a node per kind depending on every module of the
previous kind, forcing the levels structurally. It works and is explicit, but it puts
non-module nodes into a graph whose every other node is a module, and `ordered()` would
have to filter them back out.

`/ai:decide` has settled this in favour of the explicit key; the reasoning, the rejected
alternatives, and the boundary the choice lives behind are recorded under Build-vs-Adopt
Decisions below.

### Decision 2: A cross-phase inversion is inexpressible, not merely refused

The barrier survives only if no edge ever runs from a higher kind depth to a lower one.
Rather than validating for such an edge and rejecting it, the design admits no way to write
one: dependencies are declared on `KindSpec` between kinds, and the app axis contributes
ordering but not edges. There is no syntax whose meaning would be "app X's `urls` before
app Y's `models`".

This is the concrete cost of the guarantee, and it should be stated rather than discovered:
if per-app dependencies are ever added, they may only order apps *within* a kind depth. The
intuitive reading — "everything of app B before anything of app A" — is precisely what
breaks the barrier, and would have to be refused.

### Decision 3: Load order and enumeration order stay separate

`Registry.by_kind` continues to sort by canonical identifier. Load order is a mechanism;
enumeration order is a contract, and the two answer different questions. Alphabetical
enumeration is already relied upon by `typed-registry-stubs/spec.md`, which requires
canonical-identifier emission so that unrelated changes do not churn a committed stub, and
by `framework-lifecycle/spec.md`, which specifies hook payload order the same way.

Odoo conflates the two — contributions arrive in load order — and pays for it with results
that shift when an unrelated module is installed. Keeping them separate means the
components a hook *receives* are ordered by identifier while the modules whose hooks *fire*
are ordered by load order. That is two orders in one system, which is a real cost; the
alternative is one order that changes meaning depending on the installed set.

If a surface ever genuinely needs dependency-ordered components — middleware is the usual
example — that is a second, separately named projection, not a redefinition of this one.

### Decision 4: No per-app dependency declaration in this change

The motivating need — models processed before views consume them — is satisfied by the
barrier, which is what this change states. Per-app dependencies would serve a different
need: ordering *within* a kind depth, across apps, for hook side effects. No such case
exists in the project today.

Django has run twenty-one years with no per-app dependency declaration, using
`INSTALLED_APPS` order and a load-phase barrier — the same two mechanisms this change
states. Odoo needs `depends` because its addons are acquired independently and no single
author sees the whole list; `spoc.toml` has exactly one author who sees exactly that.

Adding an ordering key later is additive and cheap. Removing one after the stable release
is impossible. The stated tiebreak in Decision 1 is the escape hatch in the meantime: an
author who needs one app's hooks before another's reorders `[spoc.apps]`.

## Build-vs-Adopt Decisions

Recorded by `/ai:decide`; mirrored project-wide in `DECISIONS.md`. Concrete tool names live
here and there only — `specs/` stays abstract.

### Decision: The load-ordering guarantee — Extend `graphlib` with an explicit `(kind_depth, app_index)` key

- **Status**: approved
- **Why**: CPython defines `static_order()` as the `get_ready()`/`done()` loop, so kind-phase
  batching is documented behaviour and the barrier itself is not an accident. Within a level
  the documentation promises nothing — it says only that the order "may depend on the
  specific order in which the items were inserted in the graph", a caveat rather than a
  contract. The app-list tiebreak this change states is exactly that unpromised half, and it
  holds today only because `_register_apps` happens to insert app-major. Sorting by
  `(kind_depth, app_index)` puts the guarantee where a reader of our code can check it, and
  satisfies every edge by construction, since `depends_on` runs only from a lower depth to a
  higher one. The shape is standard rather than invented: Odoo's module graph sorts by
  `(phase, depth, order_name)`, and networkx exposes the same idea as
  `lexicographical_topological_sort(key=…)`.
- **Considered**: adopt `graphlib` as-is and document the level-order behaviour (zero code
  change and not wrong, but the guarantee then holds for a reason invisible in our source,
  and rests on a documented caveat); canonicalise graph insertion order so `static_order()`
  yields the intended sequence (makes the artifact deliberate instead of replacing it, and
  still leans on insertion order being honoured within a level);
  `networkx.lexicographical_topological_sort(key=…)` (precisely the primitive wanted, mature
  and well documented — hard-rejected on the zero-runtime-dependency invariant,
  `dependencies = []`, not on quality).
- **Scope — borrow the idea, not the library**: what is taken from networkx is the `key=`
  parameter's premise, that a topological order with a stated tiebreak is a sort by an
  explicit key. What is deliberately not taken is anything that would amount to
  reimplementing a graph library: no general graph type, no traversal API, no second sort
  strategy, no path or reachability helpers. The whole of it is one two-element tuple over
  data the kernel already holds — the kind's depth and the app's position — and a `sorted()`
  call. If a future need pulls toward general graph algorithms, that is the signal to revisit
  this decision and adopt rather than grow this one.
- **Isolation**: `Loader.ordered()`, the single method that turns the module graph into a
  sequence. `_register_apps` keeps building the graph exactly as it does now, and nothing
  else in the kernel learns what a kind depth is.

### Decision: Cycle detection and its error — Adopt `graphlib`, unchanged

- **Status**: approved
- **Why**: an ordering key sorts a DAG but cannot notice that the kind graph is not one.
  `graphlib.TopologicalSorter.prepare()` already detects cycles and reports one with its
  first and last node identical, which is what `CircularDependencyError` names today. Keeping
  it means the sort key never has to prove acyclicity and the error contract does not move.
  This also settles task 1.2: both candidates were standard library, so the
  zero-runtime-dependency invariant was never in tension and the gate turned on ownership of
  the guarantee rather than on acquiring anything.
- **Considered**: finding cycles inside the depth computation (a longest-path walk can detect
  a back edge, but it restates what `prepare()` does and would have to reproduce the cycle
  report the existing error message is built on); no detection at all, trusting declaration
  validation (a cycle becomes unbounded recursion or a silently truncated order — the
  project's rule is loud failure or nothing).
- **Isolation**: unchanged — the `except graphlib.CycleError` clause in `Loader.ordered()`,
  raising `CircularDependencyError` with the same message from the same place.

## Risks / Trade-offs

- **The tiebreak makes `[spoc.apps]` order semantic.** Reordering the list becomes a
  behavioural change for any project relying on hook order. This is Django's bargain with
  `INSTALLED_APPS` and it has held; the alternative is leaving the order undefined, which
  is what we are here to stop doing.
- **Two orders in one system** (Decision 3) is a thing a reader must learn. Mitigated by
  stating both in the specs and by the fact that only one of them — enumeration — is
  visible to code that does not write lifecycle hooks.
- **Stating the barrier forecloses per-app kind subsets in their obvious form.** That
  feature would have to preserve the barrier deliberately. Making that constraint visible
  now, while nothing depends on either, is the point.
- **The change is invisible if it works.** No user-facing behaviour moves, so its value is
  entirely in what it prevents later. That is the correct shape for a one-way-door decision
  taken before a stable release, and a poor shape for a change judged by its diff.
