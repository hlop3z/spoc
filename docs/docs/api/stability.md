# Stability & Versioning

What SPOC promises about its own surface, and what it deliberately does not.

Every name you can import, every command you can run, every extra you can install
carries exactly one **tier**. The tier is the promise.

For anything importable, the tier is not written down anywhere separately — it
follows from how the name is exposed, so the code and the promise cannot drift
apart. [The rules are three lines](#how-a-name-gets-its-tier), and CI checks that
every exposed name resolves cleanly under them.

## The three tiers

| Tier | May break in a patch | May break in a minor | May break in a major |
| --- | --- | --- | --- |
| **`public`** | no | no | yes — after deprecation |
| **`provisional`** | no | yes | yes |
| **`internal`** | yes | yes | yes |

**`public`** is the bulk of the surface: everything importable from `spoc` directly,
plus `spoc.formats`, `spoc.testing`, `spoc.diagnostics`, `spoc.scaffold`, the `spoc`
command, the pytest fixtures, and the extras.

**`provisional`** is public and documented, but not yet settled. It says so in its own
docstring — if you read a docstring containing *"may change incompatibly in a minor
release"*, that is the mark. A provisional docstring also tells you *what would settle
it*: the open question, or the condition under which the name becomes `public` or is
withdrawn. If it only hedges and never says, that is a defect, and the surface check
fails on it.

**`internal`** is everything else, and `spoc.core` in its entirety.

### What `spoc.scaffold` publishes

A name is exported from `spoc.scaffold` only if you must write it to do something the
package offers — invoke an operation, implement a contract it accepts, distinguish a
failure you can respond to differently, or supply a value it reads.

Everything else stays in the module that defines it: the retrieval ports and their
adapters (`Fetcher`, `Cache`, `HttpFetcher`, `DirectoryCache`, `RemoteTemplateSource`),
archive admission, the record-*writing* half of provenance, and the error leaves whose
only distinct response is a different sentence in a message you did not write.

!!! note "Withdrawn is not unreachable"
    Those names still import fine from their own modules — `from spoc.scaffold.errors
    import PathEscapeError` works and will keep working. What changed is what is
    promised, not what is reachable. Reaching an internal element is not a promotion,
    so a submodule import buys you no stability guarantee.

!!! warning "Being importable is not a promise"
    `spoc.core` holds the kernel: the declaration layer, the loader, the config
    adapter. Nothing in it is stable, however easy it is to reach. If you need
    something that is only available there, that is a gap worth reporting — not an
    API to import.

Anything that does not resolve to `public` or `provisional` is `internal`. Absence of a
promise is never a promise.

## How a name gets its tier

Three rules, applied to the name as the package exposes it:

| If the name is… | its tier is |
| --- | --- |
| listed in a package's `__all__` | **`public`** |
| …and its docstring says *"may change incompatibly in a minor release"* | **`provisional`** |
| reachable only through a submodule, never re-exported by the package | **`internal`** |

So `spoc.Framework` is public because `spoc/__init__.py` exports it.
`spoc.testing.core.mode` is internal because you can only get at it by importing
`spoc.testing.core` directly — the promise is on `spoc.testing`, not on the module
underneath it. And `spoc.scaffold.Origin` is provisional because it says so, and says
what would settle it:

```python {test="skip"}
@dataclass(frozen=True, slots=True)
class Origin:
    """The template set a project was generated from.

    Provisional: may change incompatibly in a minor release. It settles when the
    project decides whether the record must also carry the substitution values a
    generation used — the project name, app name, and kinds.
    """
```

That means **the way to check a tier is to read the code** — the export list and the
docstring — rather than to look it up in a table that might be stale.

!!! note "What is still declared by hand"
    Six kinds of thing carry no importable name, so nothing can read a tier off them:
    the `spoc` command, the pytest plugin entry point, the fixtures, the extras, the
    `spoc.toml` schema, and the template set. Those are listed explicitly in
    `[tool.spoc.stability]` in `pyproject.toml`. Importable names are not, and putting
    one there is refused.

## What is not covered

Even on a `public` element, these are free to change at any time:

- **Message text.** Error *types* and their hierarchy are public — `SpocError` will
  keep catching everything, and `UnknownKindError` will keep being raised where it
  is raised. The wording inside the message is not. Match on the type, never the
  string.
- **Prose output.** `spoc projection`'s document and the `--json` output of
  `spoc check`, `spoc list`, and `spoc explain` are public. The human-readable
  rendering of the same commands is free to be reformatted.
- **Pinned versions inside an extra.** `spoc[yaml]` will keep giving you YAML
  support; which library provides it, and at which version, may change.
- **Internal attributes and reprs** of otherwise-public types.
- **What you do with a resolved component.** Resolution is covered; the object's
  lifetime afterwards is not. A component resolved before a lifecycle transition
  and used after it is outside the contract — SPOC returns the object and never
  observes the use. Ordering that is the caller's, and in a served application it
  is the server's; see [Shipping a framework](../how-to/ship-a-framework.md).

## The pre-1.0 allowance is spent

While SPOC was pre-1.0 there was one explicit allowance:

> **A `public` element may change incompatibly in a minor release, without a
> deprecation period, until the first stable major release.**

**That allowance ended when 1.0 was cut.** From 1.0, an incompatible change to a
`public` element ships only in a major release, and only after the deprecation
lifecycle below has run in full. Nothing re-opens it: releasing under another
`0.x` version would not bring it back.

A major bound is the pin that now matters:

```toml
# pyproject.toml
dependencies = ["spoc>=1.0,<2"]
```

## Deprecation

A `public` element is never removed abruptly. It goes through this, in
order:

1. It is **marked deprecated**, and its documentation names the replacement — or
   states plainly that there is none.
2. Using it raises a **`DeprecationWarning`** naming the element and its
   replacement. Standard warning filters apply, so you can silence it or turn it
   into an error:

    ```python
    import warnings

    warnings.simplefilter("error", DeprecationWarning)
    ```

3. It stays present and working for **at least one full minor release**.
4. Only then may a **major** release remove it.

Nothing is ever deprecated and removed in the same release, and nothing is removed
without a warning having been available first.

None of that rests on anyone remembering it. `apidiff` reads the mark out of every
published release behind the one being cut, so a removal has to show its own
history: which release first marked it, and that a full minor release shipped in
between with the element still working. A patch release does not count — the wait
is measured in minor releases, so `0.6.1` shipping after `0.6.0` marked something
is still one release, not two.

Where that history cannot be established — an element marked as far back as the
tags go, or no tags to read — the removal is reported `undetermined` and the run
exits non-zero. "Nobody could tell" is never reported as "the lifecycle was
completed".

## What had to be true before 1.0

These were the criteria, checkable rather than a matter of taste. All three held
when 1.0 was cut, and they are kept here unchanged — the release met them; it did
not rewrite them:

- [x] Every element of the surface resolves to a tier, and `apicheck` passes.
- [x] Nothing intended to be `public` at 1.0 is still `provisional`. Every
      exposed name has had its intended tier decided, and each name still
      `provisional` states the condition that would settle it. Two kinds remain,
      both deliberately: elements whose shape is genuinely undecided, and the four
      command mount points, which stay open until a framework outside SPOC has
      mounted them or SPOC commits to a parser choice. Neither is waiting on a
      decision nobody has made — being unsettled past 1.0 is what `provisional`
      is for.
- [x] The deprecation lifecycle has been exercised on a real element, not only
      documented and tested. `spoc.scaffold.extract_archive` ran the whole
      course: marked and warning in `0.6.0` (steps 1 and 2), still present and
      working through `0.7.0` and `0.8.0` (step 3), removed in `1.0.0` (step 4).
      The function itself never moved — `spoc.scaffold.archive.extract_archive`
      is what the warning named and what still works. That is a lifecycle that
      ran, not a mechanism that was merely tested.

1.0 was cut because those held — a consequence of meeting them, not a decision
made independently of them. The `Development Status` classifier tracks the same
line, and moved to `5 - Production/Stable` in the same release.

## Checking the contract yourself

Two commands, two questions. Both run in CI on every push.

**Is the surface self-consistent right now?**

```bash
cd scripts/py && uv run apicheck ../..
```

It fails if an exposed element resolves to no tier, if the manifest declares a
non-import element the surface no longer exposes, or if the surface exposes one the
manifest never declared. It also fails if an element is marked deprecated without
naming a replacement or saying there is none, and if a `DeprecationWarning` is
raised anywhere outside `spoc.core.deprecation` — withdrawal has exactly one
spelling, because the absence of a mark can only mean "not being withdrawn" if
there is one way to write one. Kinds it cannot observe are reported `unverifiable`
and counted, never silently passed.

**What changed since the last release?**

```bash
cd scripts/py && uv run apidiff ../..
```

It reports every element added, removed, or moved between tiers since the last
release tag, every incompatible change, every withdrawal currently in flight, and
for each removed element whether its deprecation lifecycle was completed. Before
1.0 it reported without failing — the allowance permitted those changes, so failing
on one would have contradicted the policy. Now it fails.

The increment matters as well as the change. A breaking change is what a
major release is *for*, so incompatible changes are permitted there and refused
everywhere else; an incomplete withdrawal is refused in every increment, because
completing the lifecycle is what earns the removal a major release is allowed to
make. Exit `1` means it found a problem; exit `2` means it could not finish the
comparison — an unresolvable baseline, or a withdrawal history it could not
establish — which is deliberately never `0`.

Which means the table at the top of this page is not a description of intent — it is
enforced.
