# Stability & Versioning

What SPOC promises about its own surface, and what it deliberately does not.

Every name you can import, every command you can run, every extra you can install
carries exactly one **tier**. The tier is the promise. Tiers are declared in
`[tool.spoc.stability]` in `pyproject.toml` — one list, checked against the real
surface on every CI run, so this page cannot quietly drift away from the code.

## The three tiers

| Tier | May break in a patch | May break in a minor | May break in a major |
| --- | --- | --- | --- |
| **`public`** | no | no | yes — after deprecation |
| **`provisional`** | no | yes | yes |
| **`internal`** | yes | yes | yes |

**`public`** is the bulk of the surface: everything importable from `spoc` directly,
plus `spoc.formats`, `spoc.testing`, `spoc.diagnostics`, the stable half of
`spoc.scaffold`, the `spoc` command, the pytest fixtures, and the extras.

**`provisional`** is public and documented, but young. It says so in its own
docstring — if you read a docstring containing *"may change incompatibly in a minor
release"*, that is the mark. Today this is the remote template acquisition and
provenance surface in `spoc.scaffold`, which landed recently and has had no use in
the wild yet.

**`internal`** is everything else, and `spoc.core` in its entirety.

!!! warning "Being importable is not a promise"
    `spoc.core` holds the kernel: the declaration layer, the loader, the config
    adapter. Nothing in it is stable, however easy it is to reach. If you need
    something that is only available there, that is a gap worth reporting — not an
    API to import.

Anything that appears nowhere in the manifest is `internal` by default. Absence of a
promise is never a promise.

## What is not covered

Even on a `public` element, these are free to change at any time:

- **Message text.** Error *types* and their hierarchy are public — `SpocError` will
  keep catching everything, and `UnknownKindError` will keep being raised where it
  is raised. The wording inside the message is not. Match on the type, never the
  string.
- **Prose output.** A command's `--json` output is public. The human-readable
  rendering of the same command is free to be reformatted.
- **Pinned versions inside an extra.** `spoc[yaml]` will keep giving you YAML
  support; which library provides it, and at which version, may change.
- **Internal attributes and reprs** of otherwise-public types.

## Before 1.0

SPOC is pre-1.0, and there is one explicit allowance that comes with that:

> **A `public` element may change incompatibly in a minor release, without a
> deprecation period, until the first stable major release.**

That allowance ends the moment 1.0 is cut. It is not extended by re-releasing under
another `0.x` version once the criteria below are met.

Pin a minor version if that matters to you:

```toml
# pyproject.toml
dependencies = ["spoc>=0.5,<0.6"]
```

## Deprecation, once 1.0 lands

After 1.0, a `public` element is never removed abruptly. It goes through this, in
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

## What has to be true before 1.0

These are the criteria, and they are checkable rather than a matter of taste:

- [ ] Every element of the surface has a tier, and `apicheck` passes.
- [ ] Nothing intended to be `public` at 1.0 is still `provisional`.
- [ ] The deprecation lifecycle has been exercised on a real element, not only
      documented and tested.

1.0 is cut when those hold — it is a consequence of meeting them, not a decision
made independently of them. The `Development Status` classifier tracks the same
line: it stays pre-stable while the allowance above is in force.

## Checking the contract yourself

The manifest is data, and the check is a command:

```bash
cd scripts/py && uv run apicheck ../..
```

It fails if the surface exposes anything the manifest does not declare, if the
manifest declares anything the surface no longer exposes, or if a `provisional`
element forgets to say so. Which means the table at the top of this page is not a
description of intent — it is enforced.
