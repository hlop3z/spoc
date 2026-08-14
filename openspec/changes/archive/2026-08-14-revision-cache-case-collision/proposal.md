# Distinct revisions must stay distinct on the host that stores them

## Why

`remote-template-acquisition` already requires that two distinct revisions never
resolve to the same retained content. The retention mapping satisfies that as string
equality and no further: a revision that is usable as a path segment is used verbatim.
On a host whose path equivalence is coarser than string equality — the majority of
developer machines — two distinct revisions then land in one directory, and one
revision is served the other's content. That is the single outcome the requirement
exists to forbid.

It is not theoretical, and it is live: the property test
`test_distinct_revisions_never_share_retained_content` fails today with `L` and `l`,
and the unit suite runs on all three declared platforms, so this fails CI as soon as
the random search draws such a pair. Two independent instances were confirmed on the
host: names differing only by letter case share a directory, and a name ending in `.`
is stored under the name without it. The second is invisible to the current property
test, which compares locations rather than asking whether the host can tell them
apart — so the guard that should have caught this class only catches half of it.

## What Changes

- The retention mapping's verbatim branch narrows to revisions the host is guaranteed
  to store under the name given. Every other revision takes the derived name the
  mapping already produces, which is total and already collision-free.
- The injectivity property is judged against a model of the coarsest host equivalence
  rather than against location equality, so the whole class is covered rather than the
  instance that happened to be observable.
- **BREAKING (cache only)**: revisions that previously stored verbatim under a
  mixed-case or trailing-dot name now store under a derived name. The affected content
  is re-retrieved once. No public API, no generated project, and no configuration
  changes.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `remote-template-acquisition`: the requirement that a revision names its own
  retained content and no other states that distinctness is judged by the storage
  host's own notion of sameness, not by the revision strings differing. A revision the
  host cannot store faithfully under its own name must be given a derived name, never
  a name the host may already be using for something else.

## Critical concerns

- **Injectivity of the revision-to-location mapping** (correctness): the mapping must
  remain total and collision-free under any host's path equivalence. Whether that is
  realized by an adopted name-sanitizing component or by the mapping already present is
  a build-vs-adopt decision, recorded by `/ai:decide` before implementation.

## Impact

- `src/spoc/scaffold/cache.py` — `DirectoryCache._entry`, and the docstring stating
  what the mapping guarantees.
- `tests/test_properties.py` — the injectivity property's equivalence model.
- `tests/test_scaffold_cache.py` — cases pinning which revisions stay verbatim.
- Retained caches on users' machines: a one-time re-retrieval for affected revisions.
  Superseded directories are left in place; nothing in this cache expires.
