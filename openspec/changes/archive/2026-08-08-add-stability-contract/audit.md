# Surface audit

The evidence behind the tier assignments in `[tool.spoc.stability]`. In-flight note for
this change; it archives with it. The manifest is the source of truth — this file records
*why* each call was made, so a later reader does not have to re-derive it.

Enumerated with the adopted tool, not by hand:
`griffe dump spoc -s src` → 111 exported names across five packages.

## The rule applied

Two objective tests, in order:

1. **Is it reachable only through `spoc.core`?** → `internal`, unless a *present-day*
   consumer needs it (documented example, scaffold template, or reference app).
2. **Did it enter the surface in the last two change cycles?** → `provisional`. Surface
   that has survived a full cycle unchanged is `public`.

Test 2 is answered from git, not memory: `git log -S'"<name>"' -- <module>/__init__.py`.

## `spoc.core` — internal, with one promotion

`spoc/core/__init__.py` re-exports nothing and declares no `__all__`, so every name under
it was implicitly public by the underscore convention. That is the hedge this change ends.

**Promoted: `component`** (`spoc.core.declaration.component` → `spoc.component`).

Evidence, both present-day:

- `docs/docs/tools/testing.md:20` instructs users to write
  `from spoc.core.declaration import component`, and carries a note explaining *why* you
  would reach for it — a documented public example importing from an internal path.
- `tests/conftest.py:19` uses the same import in the shared fixture body.

Everything else under `spoc.core` stays internal. `KindSpec`, the seventeen exceptions,
`Identifier`/`parse`/`compose`, and `Registry`/`Component` were already re-exported at the
top level, so no consumer needs the internal path for them. `Internal`, `as_kind_spec`,
`check_metadata`, `registrar`, `is_spoc`, `get_info`, `discover`, and everything in
`loader`, `config`, and the remaining `identity` helpers have no external consumer.

In-repo tests import `spoc.core.config` and `spoc.core.exceptions` directly. That is not
evidence for promotion: `internal` withholds a promise from *external* consumers, and the
suite ships with the code it tests.

## `spoc.scaffold` — split 22 public / 27 provisional

The split is the commit that introduced each export, not a judgement call:

| Origin commit | Names | Tier |
| --- | --- | --- |
| `54f02a2` *add the project scaffolder behind `spoc init`* | 22 | `public` |
| `a5496fd` *export and document the retrieval surface* | 24 | `provisional` |
| `b0ebb1a` *reserve the origin record's destination* | 3 | `provisional` |

The 27 provisional names are the remote-acquisition and provenance surface, both landed in
the two change cycles archived on 2026-08-05 and 2026-08-07. They have a behavior spec, but
a spec contracts *behavior*, not Python names — and these names have had no external use at
all. Provisional is the honest tier for two-day-old signatures.

### Open question 2.3, resolved: the template set format is `public`

The design left this open. Applying test 2: the template set contract — the `default/`
layout, `.tmpl` suffixes, `$placeholder` substitution, and the `ENTRY_POINT_GROUP` under
which third-party sets register — all entered at `54f02a2` and survived two subsequent
change cycles, including the remote-template work, unchanged.

What is new is not the format but the *acquisition* of sets over the network. So the
contract splits along the same seam as the names: the set format is `public`, remote
retrieval is `provisional`.

## Packages taken whole

`spoc` (26 → 27 with `component`), `spoc.formats` (23), `spoc.testing` (5), and
`spoc.diagnostics` (8) are `public` in full. Each has a behavior spec in `openspec/specs/`
and predates the last two cycles.

## Submodule paths are internal

`spoc.cli`, `spoc.diagnostics.core`, `spoc.diagnostics.locate`, `spoc.diagnostics.cli`,
`spoc.scaffold.cli`, `spoc.testing.core`, and `spoc.testing.tree` each declare their own
`__all__`, so griffe reports them as public. They are declared `internal`: every name they
hold is already reachable at its package's top level, and the package path is the promise.

## Two surfaces that are not importable names

- **pytest fixtures.** `spoc_framework`, `spoc_isolated`, and `spoc_tree` are depended on
  *by name* in a test signature, never imported. They are `public` as fixtures. The
  importable module `spoc.testing.plugin` that supplies them is `internal` — pytest loads
  it through the entry point, and no consumer should import it.
- **The console script and its output.** The `spoc` script is `public`; so is its
  machine-readable output. `spoc.cli:main` — the import path behind it — is `internal`.
