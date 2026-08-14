# Design: reading one facet costs the facet

## Context

`Registry` holds one flat `dict[str, Component]` keyed by canonical identifier, plus a
divergence map. `resolve` is a single dict hit — 0.35 µs at 50k components. Every other
read (`all`, `by_kind`, `by_namespace`, `namespaces`, and all three navigation levels)
goes through `_snapshot()` + filter + sort: O(n log n) per question, where n is the
whole registry. Navigation compounds it — one `objects.models.blog.post` walk asks two
such questions (namespaces of the kind, then names of the namespace) and measured
10.6 ms at 50k, 30,000× the cost of `resolve` for the identical record.

Two facts make the fix trivial where it would normally be a design problem:

- **The registry is add-only.** Nothing removes or renames a record; the lifecycle
  spec's post-boot guarantee is built on exactly this. An index maintained at
  registration can therefore never go stale — there is no invalidation, only growth.
- **All mutation already serializes through one lock.** Updating an index inside that
  locked region inherits the atomicity the spec already requires; no new coordination
  is introduced.

## Goals / Non-Goals

**Goals:**

- Navigation steps and faceted reads answer in time proportional to their facet.
- Zero observable behavior change: identical records, identical error candidates,
  identical deterministic ordering, identical thread-safety guarantees.
- A test that pins the *scaling property* rather than a wall-clock number, so CI
  machines of any speed judge it identically.

**Non-Goals:**

- No change to `resolve` (already O(1)) or to the failure path's documented O(n)
  precision walk — failure is worth a scan, and its one-observation guarantee depends
  on scanning a single snapshot.
- No caching of *sorted* results. Sorting stays at the read, on the facet; caching
  sorted lists would trade memory for a second copy of every answer and buy little —
  sorting a facet is cheap once the facet is small relative to the registry.
- No public API surface change of any kind.

## Decisions

### D1 (revised in review) — One store keyed by segments, not a store plus an index

**The first implementation of D1 was built and then replaced.** It added a nested facet
index beside the flat store, which worked and was fast, but it required amending the
`Single flat store` requirement — grouped views must be "derived from the registry, never
maintained as independent state" — because an index *is* maintained state. Review
pushed back on that amendment, correctly: the original rule is a **structural**
guarantee (with one store, drift is unrepresentable), and the replacement was a
**procedural** one (a promise that future writes stay in step). Procedural guarantees
rest on invariants a later edit can silently void — add a `remove()`, a rename, a
bulk-load path, and the proof evaporates while the tests still pass.

The resolution keeps both properties instead of trading one for the other: **the store
itself is keyed by the grammar's segments** — kind → namespace → object name — and the
flat identifier-keyed dict is *deleted*, not supplemented. A facet is then a
sub-dictionary of the one store. There is no second structure, so there is nothing to
drift, and the original requirement stands unamended.

This costs no fidelity because the code already argued it does not: `resolve`'s own
comment records that `parse` transforms nothing and the grammar admits neither `:` nor
`.`, so `str(parse(x))` is `x`. Reaching a record by three segments and by its composed
string are the same lookup written two ways.

Two consequences worth stating:

- **`resolve` success costs three dict hits instead of one** — measured 0.31 → 0.42 µs.
  A real regression on the hottest path, accepted for what it buys.
- **`resolve` *failure* got 102× faster** (6,500 → 63.5 µs), unplanned: the failure path
  no longer copies every record to find candidates, it reads the two levels it can name.

The identity map (`_identifier_of`) survives as genuinely non-derivable state — it
answers the inverse question, which segments an object was registered under, and cannot
be read off a facet. That is what D1a addresses.

### D1a — One mutator, enforced by a test (the process, not the promise)

Single-store solves facets structurally; it does not cover the identity map beside them.
So the registry has exactly one method that writes state — `_admit`, called with the
lock held — and a test parses the module's AST and fails if any method outside
`__init__`/`_admit` assigns to, deletes, or in-place-mutates a state attribute. A second
test asserts the enumerated state list matches the object's real attributes, so the
first cannot silently fall behind the class.

The guard was mutation-checked before being trusted: a plausible future edit (a bulk-add
that updates the store and the count but forgets the identity map) makes it fail, naming
the method and the attributes it touched.

That is the durable part. It converts "we were careful" into "you cannot stop being
careful without the suite saying so", and it makes adding future state a decision with a
prompt attached rather than an omission.

### Superseded: the original D1 — a nested facet index beside the store

`Registry` gains `_facets: dict[str, dict[str, dict[str, Component]]]` — kind →
namespace → object name → record — written in the same locked block that admits the
registration into `_store`. Reads snapshot the relevant level under the lock (a
`tuple(...)` of keys or values — O(facet)) and sort outside it, exactly the pattern
`_snapshot()` already uses.

Alternatives considered:

- **Index inside navigation** (memoize per `_Level`): rejected — levels are created
  per walk, so the memo would rebuild per access; hoisting it to a shared cache
  reintroduces invalidation that the registry-side index gets for free.
- **Sort at write, binary-insert into lists**: rejected — moves cost into the lock,
  buys nothing the read-side sort of a small facet doesn't already provide, and
  complicates the atomicity argument.
- **Adopt an indexing structure** (sortedcontainers or similar): foreclosed by the
  enforced empty dependency set, and unnecessary — the index is two levels of the
  standard library's dict, whose insertion-order iteration also keeps enumeration
  deterministic.

### D2 — Faceted readers move onto the index; `all()` stays on the store

`by_kind`, `namespaces(kind)`, and navigation's `_namespaces()`/`_object_names()`
read the index. `all()` and `__iter__` keep reading `_store` — they genuinely are
whole-registry questions, and their O(n log n) is their honest cost. `by_namespace`
(namespace across kinds) iterates the kinds' second level rather than the whole
store: O(kinds + facet), and kinds are a small closed set.

Navigation currently uses only public `Registry` methods. It moves to the faceted
readers (`namespaces(kind)` exists already; an object-names read is added as an
internal method). Internal attributes and methods of a public type are excluded from
the stability contract by the published exclusions list, so this is not a surface
change.

### D2a — The success path asks membership, not order (added during apply)

Indexing alone took a 50k-component walk from 10.62 ms to 25.7 µs, and the benchmark
then showed where the remainder sat: every *successful* step still built and sorted its
facet, and the success path never reads that order. Sorting exists for two consumers —
the candidate list in a failure message, and `__dir__` — neither of which runs when the
step succeeds under the name as written.

So `Registry.holds(kind, namespace=None, object_name=None)` answers the membership
question at whatever depth the caller has reached, and navigation asks that first,
falling back to the ordered facet only when it misses. The fallback is still needed and
still correct: an escaped spelling (`class_` for `class`) matches by comparing against
each candidate, and a failure must name them.

This is the shape `resolve` already has — O(1) on success, O(facet) on the failure path
where precision is worth the walk — which is the coherence argument for it as much as
the speed. Final: **1.72 µs per walk, 6,175× the original**, within 5.4× of `resolve`,
where the remainder is attribute dispatch and level allocation rather than scanning.

### D3 — The scale test asserts the ratio, not the clock

The property is "cost tracks the facet": measured as *navigation cost at N components
vs at k·N components in other facets* staying within a constant factor, with a
generous bound. Wall-clock thresholds are machine-dependent and flake; ratios of the
same operation on the same machine in the same process are not. The existing
50k-component measurement becomes the regression scenario.

### Build-vs-adopt

Nothing external enters. The one candidate (an indexed container library) is rejected
in D1 for the same reason recorded throughout this project: `dependencies = []` is an
enforced invariant, and two nested stdlib dicts are the entire mechanism.

## Risks / Trade-offs

- **Memory: every record is referenced twice** (store + index leaf) → References,
  not copies — a pointer per component. At 50k components this is one small dict
  spine per kind/namespace. Accepted.
- **Two structures that must agree** → Both written in one locked block; the property
  suite's generated-operation-sequence test already exercises concurrent
  register/enumerate interleavings and will now exercise the index on its read side.
  A disagreement is unrepresentable short of editing one write site and not the
  other, which the scale + equivalence tests then catch.
- **Ratio tests can still flake under extreme CI noise** → The bound is set an order
  of magnitude looser than the fix's actual effect (constant-factor vs 30,000×);
  noise of that magnitude fails the machine, not the test.

## Migration Plan

None. Internal state of one class; revert is `git revert`.

## Open Questions

_None._
