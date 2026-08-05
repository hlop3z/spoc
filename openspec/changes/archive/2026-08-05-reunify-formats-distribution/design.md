# Design — Reunify the Formats Distribution

## Context

`production-hardening` (archived 2026-08-04) split `spoc.formats` into its own
distribution (design.md D8 + the "Multi-distribution packaging — Adopt uv
workspaces" ADR). The owner has re-decided the bounded-context question: formats is
a capability of the connection kernel, not its own context. Nothing is published —
`v0.5.0` is untagged and `spoc-formats` never reached PyPI — so the reversal is a
clean edit of unreleased work, not a migration.

## Goals / Non-Goals

**Goals:**

- One releasable artifact: `spoc`, containing `spoc.formats` as a contained
  subpackage, extras restored (`yaml`, `xml`, `toml`, `query`, `full`).
- The bare install keeps `dependencies = []` — extras are the feature flags.
- The two real defects the split fixed stay fixed, now enforced by tests instead of
  packaging: the kernel never imports `spoc.formats` (importing `spoc` never loads
  it), and `FormatError` never subclasses `SpocError`.

**Non-Goals:**

- No behavior change in any formats capability (codecs, collection, addressing).
- No renaming of the formats API itself — only its import path
  (`spoc_formats` → `spoc.formats`).
- No second repo, no re-litigating uv itself (the "Adopt uv" ADR stands).

## Decisions

### D1: Single distribution; the boundary moves from packaging to tests

`src/spoc/formats/` holds the five modules unchanged except for import renames.
Containment is pinned by a boundary test: import `spoc` in a fresh interpreter and
assert no `spoc.formats.*` module is loaded and `FormatError` is not a `SpocError`.
This is strictly stronger than the workspace gave in practice — packaging separation
never actually prevented an import; the test fails the suite the moment anyone adds
one.
**Alternatives rejected:** keeping two artifacts (operational cost with no current
benefit — nothing is published, one team, one cadence); the hybrid re-export
(`spoc` depending on `spoc-formats`) — reintroduces a kernel→formats dependency
direction the boundary rule forbids.

### D2: Extras return to `spoc`; the dev group consumes them by self-reference

`[project.optional-dependencies]` moves to the root `pyproject.toml` verbatim, with
`full = ["spoc[yaml,xml,toml,query]"]` self-referencing. The dev group's
`spoc-formats[full]` entry becomes `spoc[full]` through the existing
`[tool.uv.sources]` mechanism collapsing to the project itself — uv resolves a
self-referential extra in a dependency group. The formats suite keeps meaning
something because the extras install with a plain `uv sync`.

### D3: Version, changelog, and ADR are edited, not migrated

0.5.0 is untagged: the CHANGELOG's existing 0.5.0 split entry is rewritten to
describe the contained subpackage (greenfield rule — the changelog tells the truth
about what 0.5.0 ships, not the intra-development back-and-forth). `DECISIONS.md`'s
multi-distribution ADR is marked superseded with a pointer to this change; D8's
reasoning stays in the production-hardening archive untouched.

### Build-vs-adopt

The only tooling decision is packaging shape, already owned by the standing
"Adopt uv" ADR; dropping the workspace uses less of uv, adopts nothing new, and
builds nothing custom. No new ADR entries beyond the supersession note.

## Risks / Trade-offs

- [Kernel wheel now physically contains formats code] → It costs a few stdlib-only
  kilobytes; the import boundary — the thing that matters — is test-enforced. The
  release wheel check inverts to assert formats **is** present.
- [Future need for independent formats releases] → Re-splitting later is the same
  mechanical move; the boundary test keeps the code split-ready indefinitely.
- [uv self-referential extra in the dev group misbehaves] → Verified by `uv sync`
  + full gate run during apply; fallback is listing the four optional dependencies
  directly in the dev group.

## Migration Plan

None — nothing is published. All references (CI, docs, README, example) move in
this change set; `packages/` is deleted per Rule 5.
