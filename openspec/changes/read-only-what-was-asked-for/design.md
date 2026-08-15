## Context

Both changes are read paths in existing adapters. Neither adds a dependency, a port, or a
module; neither moves logic across the core/adapter line. `formats/operations.py` is the
adapter that reaches the filesystem for the data surface, and `diagnostics/core.py` is the
library layer under the `spoc check` / `spoc list` entry points. The CLI modules beside
them stay untouched — they render what these return, and what they return is unchanged in
type and, for `list`, in value.

Current state:

- `collect` builds `sorted(p for p in base.rglob("*") if p.is_file())` and then asks
  `_is_ignored(relative, ignore)` per surviving path. `rglob` has already descended every
  directory by the time the first skip decision is made, and `is_file()` has stat'ed every
  entry. `_is_ignored` then re-asks the same question of every ancestor segment of every
  file — the answer for a directory is recomputed once per file beneath it.
- `list_records` builds a generator over `registry.all()`, filters on `kind` and
  `namespace`, and wraps the result in `sorted(..., key=identifier)`. `Registry.all()`
  already returns records sorted by identifier (`registry.py`), and `Registry.by_kind`
  already answers the kind facet directly and pre-sorted.

The constraint that shapes both: `spoc`'s distribution has `dependencies = []` as an
invariant, so neither change may reach for a traversal or filtering library. Both are
stdlib or existing-API work, which is the reason neither carries a build-vs-adopt decision
— there is no critical concern here to rent, adopt, or build. Nothing external is being
introduced, so there is no adapter to add.

## Goals / Non-Goals

**Goals:**

- A collection's cost is set by the tree it collects, not by the tree it sits in.
- The reportable skipped set names what was actually skipped, which is what the existing
  hidden-directory scenario already says and the implementation does not do.
- A kind-narrowed listing costs that kind's facet.
- No change to what either operation collects, resolves, or reports beyond the skipped
  set's membership.

**Non-Goals:**

- No change to key derivation, the key grammar, duplicate detection, eagerness, or the
  all-or-nothing failure contract.
- No new registry reader. The kernel's read surface is closed by this change, not widened.
- No change to `Collection`'s type, `skipped`'s type, or any signature.
- No lazy or streaming collection. Eagerness is a decided property (`design.md` D4 of the
  original data surface) and is not reopened here.
- No caching of traversal results.

## Decisions

### D1: Prune during the walk with `Path.walk`, not `rglob` plus a filter

`Path.walk()` (3.12+, and 3.12 is this package's floor) yields `(dirpath, dirnames,
filenames)` and honors in-place mutation of `dirnames` — assigning `dirnames[:] = keep`
stops the walk from descending the removed entries. That is the one mechanism that makes
"skipped" mean "not traversed" rather than "traversed and discarded".

It also separates directories from files, so the `is_file()` stat per entry disappears:
`Path.walk` is built on `os.scandir`, which reports entry type from the directory read
itself on every platform this package declares.

*Alternatives considered.* `os.walk` with `topdown=True` is the same mechanism one
abstraction lower and would force `str`/`Path` conversion at every use; `Path.walk` is the
same call in this module's existing vocabulary. A recursive `iterdir` helper was rejected
as rebuilding a stdlib traversal by hand — the same mistake the `loc` line-counter made,
and the reason Rule "never reinvent the wheel" exists. Keeping `rglob` and filtering
earlier is not possible: `rglob` owns its own descent and offers no pruning hook.

### D2: Sort the surviving files globally, preserving today's enumeration order exactly

`Path.walk` yields directory by directory, so its natural order is directory-major and
differs from the current global `sorted()` over full paths. Rather than accept an
incidental ordering change, the walk collects the files that survive pruning and sorts
that list once before reading any of them.

This keeps two things stable that would otherwise shift for no stated reason:
`Collection`'s enumeration order, and which of two colliding files
`DuplicateEntryError` names first. The sort is now `O(k log k)` over the kept files rather
than `O(n log n)` over every entry in the tree, so it is strictly cheaper than today's
even though it is the same operation.

*Alternative considered.* Sorting `dirnames` and `filenames` in place per directory and
consuming the walk lazily avoids materializing the file list. Rejected: it changes
enumeration order as an unannounced side effect of a performance change, and collection is
eager anyway, so the whole tree is held in memory a moment later regardless.

### D3: The skip predicate takes one name, not a path's every segment

`_is_ignored(relative, ignore)` asks the question of every segment of a path, which is how
the answer for a directory came to be recomputed once per file beneath it. Pruning asks it
at exactly one place — the moment a directory is a candidate for descent — so the
predicate narrows to a single entry name: hidden by leading dot, or matching an ignore
glob.

Files still get the same one-name question, because a hidden or ignored *file* is skipped
as itself. The result is one predicate, asked once per entry, replacing one asked once per
ancestor per file.

### D4: The skipped set records the pruned directory, and nothing beneath it

This follows from D1 rather than being chosen alongside it: nothing beneath a pruned
directory is enumerated, so there is nothing there to report. Reporting it anyway would
mean descending to find out — which is the cost being removed.

This is the one observable change in the proposal, and it moves the implementation toward
the spec rather than away from it: the hidden-entry scenario already reads "the directory
appears in the reportable skipped set", and today only files ever enter that set.

### D5: `list_records` chooses its reader, and takes ordering from it

```
records = registry.by_kind(kind) if kind is not None else registry.all()
```

then filters on `namespace` only, with no outer `sorted`. Both readers return records in
canonical identifier order, so the filter preserves it and the caller re-establishing it
would be a second claim to a guarantee the registry already makes — the same reasoning
`stubs/manifest.py::_entries` records for the projection's order.

The unknown-kind check stays exactly where it is and keeps raising `UnknownKindError` with
the declared kinds, before any read. `by_kind` on an undeclared kind would return empty,
and "unknown kind" must not degrade to "no records".

*Alternatives considered.* Adding a `Registry.by_kind_and_namespace` reader would make the
namespace narrowing a facet read too. Rejected: namespaces are an open set and the
namespace filter runs over records already narrowed to one kind, so it saves nothing
measurable while widening the kernel's promised read surface for a single caller. The
registry's existing `object_names(kind, namespace)` is documented as internal to the type
for the same reason.

## Risks / Trade-offs

- **`Collection.skipped` is public surface, and its membership changes.** A caller
  asserting on a file path beneath an ignored directory breaks. → The field's type is
  unchanged, so `apidiff` will not flag it; the change is recorded in the delta spec and
  the proposal marks it BREAKING for report shape. `tests/test_formats.py::
  test_ignore_patterns_extend_the_skip_set` is the one in-repo assertion of the old shape
  and is updated in the same change set. Greenfield project with no external consumers
  (recorded), so no migration shim.
- **Enumeration order could drift as a silent side effect.** → D2 exists specifically to
  prevent it; a test pinning enumeration order against a nested fixture is part of the
  task list.
- **A pruned directory that is also a legitimate data directory is now invisible.** This
  was already true — it contributed no entries before either — but its files no longer
  appear in `skipped`, so the evidence a user would debug from is thinner. → The directory
  itself appears in `skipped` under its own name, which is the actionable fact ("`vendor`
  was skipped"), and is arguably more legible than a list of every file under it.
- **`Path.walk` behavior on symlinked directories.** `follow_symlinks` defaults to False,
  matching `rglob`'s default of not following directory symlinks. → No change; the default
  is taken explicitly rather than relied on implicitly, and a test covers a symlinked
  subdirectory on the platforms that can create one.
- **`by_kind` and `all` could one day disagree about order.** → They cannot without the
  registry breaking its own stated contract, which its own suite pins. This change consumes
  that contract rather than restating it.

## Migration Plan

Not applicable. Both operations keep their signatures and return types; a caller upgrading
sees identical `spoc list` output and identical collection entries. The only difference a
caller could observe is the membership of `Collection.skipped`, for which there is no
in-flight consumer to migrate.

## Open Questions

None. Both changes are local to one function each, and the one behavioral choice — what a
pruned directory contributes to the skipped set — is settled by D4 and written into the
delta spec.
