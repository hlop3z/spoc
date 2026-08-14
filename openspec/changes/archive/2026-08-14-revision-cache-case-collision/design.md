# Design: distinct revisions stay distinct on the host that stores them

## Context

`DirectoryCache._entry` (`src/spoc/scaffold/cache.py`) maps a revision to the directory
holding its retained content. The mapping is deliberately total: a revision matching
`_SAFE_SEGMENT` (`[A-Za-z0-9._-]+`, excluding `.` and `..`) is used verbatim, and
anything else is named `rev-<sha256[:32]>`. The docstring records why filtering was
rejected — filtering is lossy, and a lossy mapping lets two revisions share one entry.

The reasoning is right and the implementation is one assumption short: it treats "the
revision is usable as a path segment" as equivalent to "the host will store it under
that name". Probed on Windows 11 (NTFS), both parts of that equivalence fail:

| Revision pair | Verbatim names | What the host does           |
| ------------- | -------------- | ---------------------------- |
| `Rev` / `rev` | distinct       | one directory — case folded  |
| `v1.` / `v1`  | distinct       | one directory — dot stripped |

macOS's default APFS folds case the same way. A trailing space would fold too, but the
space never reaches the verbatim branch — `_SAFE_SEGMENT` excludes it — so the live
exposure is exactly case folding and trailing dots. Windows reserved device names
(`con`, `nul`, `com1`) were probed and create as directories without error, so they are
not part of this defect and are out of scope.

The existing guard is `test_distinct_revisions_never_share_retained_content`, which
asserts `_entry(left) != _entry(right)`. Path comparison on Windows folds case, so the
property caught the case instance (hypothesis found `L`/`l`) — but path comparison does
*not* strip trailing dots, so the `v1.`/`v1` instance passes the guard while the
filesystem collapses it. The property tests the wrong equivalence: it asks whether two
locations differ, when the requirement is whether the store can tell them apart.

## Goals / Non-Goals

**Goals:**

- The revision-to-location mapping is injective under the coarsest host equivalence any
  declared platform applies, not under string equality.
- The guard tests that equivalence directly, so the remaining instances of the class are
  caught rather than the one instance that happened to be observable.
- Readable entry names survive for every revision the reference grammar actually
  produces today.

**Non-Goals:**

- No detection of the running host's actual filesystem semantics. The mapping is the
  same everywhere: a cache written under one host's rules must remain correct when the
  directory is later read under another's (a synced home directory, a mounted volume).
- No migration or cleanup pass over already-retained content.
- No change to the digest branch, the staging-then-publish protocol, or the cache root
  conventions.

## Decisions

### D1 — Narrow the verbatim branch; leave the digest branch alone

The verbatim branch admits a revision only when the host is guaranteed to store it
under the name given: matched by `_SAFE_SEGMENT`, not `.` or `..`, containing no
uppercase letter, and not ending in `.`. Everything else falls through to the digest,
which is already total, already collision-free, and already the mapping's answer for
"cannot be used faithfully".

This is the mapping's own logic extended by one clause, not a new mechanism — the
docstring's rule was always "verbatim when faithful, derived otherwise"; this corrects
what *faithful* means. It costs one condition at one site.

Alternatives considered:

- **Digest everything.** Simplest and uniformly correct, but it invalidates every
  retained revision rather than the affected minority, and it discards readable cache
  directories — the thing that makes a retention root inspectable when a generation
  goes wrong. Rejected: a total loss to fix a partial defect.
- **Escape-encode the unsafe characters** (`A` → `_a`, and an escape for `_`). Keeps
  names readable and is injective, but it invents an encoding the project would then
  have to specify, test, and explain, and the escape character needs its own escape.
  Rejected against Rule 7: the digest branch already covers this case, and a second
  mechanism for the same job is the duplication the rule forbids.
- **Probe the host's case sensitivity at run time** and stay verbatim where it is safe.
  Rejected: it makes the mapping a property of the machine that wrote the cache, so the
  same revision resolves differently depending on where the directory is read — the
  non-goal above, and untestable without a filesystem matrix.

### D2 — The guard tests the host equivalence, not path equality

The property asserts injectivity under an explicit model of the coarsest host
equivalence — lower-cased, trailing dots and spaces stripped — applied to the entry
name. Modelling it explicitly is what makes the trailing-dot instance visible; relying
on `Path.__eq__` is what hid it, since that models one host's rules only where the tests
happen to run.

### D2a — The search must reach the colliding region (added during apply)

Stating the equivalence was necessary and not sufficient. With the corrected model but
the original strategy — two independently drawn `st.text` values — the property still
passed at 500 examples and needed roughly 2000 to find a pair: two independent draws
almost never differ only by case or only by a trailing dot. A guard that goes red on
some runs is the failure mode that hid this defect in the first place, so the strategy
draws pairs two ways: independently for breadth, and a revision beside a neighbour of
itself (case-swapped, upper, lower, dot-suffixed, space-suffixed) for depth. It now
fails on `('A', 'a')` on every run.

The neighbourhood encodes what is already suspected, which is why it does not replace
the independent draw. Breadth is what finds the class nobody predicted; depth is what
makes the known class a regression test rather than a lottery.

### D3 — No migration, no cleanup

Content retained under a now-superseded verbatim name is orphaned: never read again,
never removed. This is consistent with the module's stated design — nothing in this
cache expires, and a directory left once is left for good. A cleanup pass would need to
distinguish orphans from entries this version still uses, which is a scan with a
failure mode of its own for content that costs one re-retrieval to replace.

### Build-vs-adopt (Rule: never reinvent the wheel)

**Concern:** injectivity of the revision-to-location mapping.
**Decision: Extend** (the mapping already present).

Adopting a filename-sanitizing component (`pathvalidate` and similar) is foreclosed
before it is compared: `dependencies = []` is an enforced invariant of this
distribution, and the scaffolder's own module docstring records the same call for
platform cache conventions — a dependency for fifteen lines would either break that
invariant or push remote templates behind an extra, reinstating the two-step install
the feature exists to remove. The sanitizing libraries also solve a different problem:
they make a name *valid*, which is the lossy filtering this mapping already rejects for
being non-injective. `hashlib` and `re` are standard library; the digest branch that
does the real work is already written. Nothing is built that does not exist.

`/ai:decide` should be run before implementation to record this in `DECISIONS.md` if a
formal ADR is wanted; the decision above is the recommendation it would evaluate.

## Risks / Trade-offs

- **A mixed-case tag loses its readable cache directory** (`V1.0` becomes
  `rev-<digest>`) → Accepted. Lowercase hex commit SHAs, `v1.2.3`-shaped tags, branch
  names, and the resolver's own `url-<digest>` keys all stay verbatim; the cases pinned
  in `tests/test_scaffold_cache.py` are unaffected.
- **One-time re-retrieval for affected revisions** → Accepted, and invisible except as
  one slower generation. The cache is an optimization; a miss is never an error.
- **Orphaned directories accumulate** → Accepted per D3, bounded by how many mixed-case
  revisions a user had already retained.
- **The equivalence model could still be too narrow** (some future host folds something
  else) → Mitigated by direction, not by prediction: the model is stated in one place
  in the test, and widening it can only push more revisions onto the digest branch,
  which is always correct.

## Migration Plan

None required. The change is confined to how a cache entry is named; a name that no
longer resolves is a cache miss, which retrieves and retains under the new name. Rollback
is reverting the commit, with the same one-time re-retrieval in the other direction.

## Open Questions

_None._
