## Why

The stability contract states that an element's tier "MUST be discoverable at its point of
definition, not only in a separate document" — and today it mostly is not. For `public` and
`internal` elements the only statement of tier is a 212-line block in `pyproject.toml`, a file
no consumer reads to learn whether a name is safe to depend on. Only `provisional` satisfies
the requirement, because it carries a notice in its own documentation.

That block is also pure restatement. Measured against the current tree, two rules already
present in the source reproduce **all 132 declared Python tiers exactly, with zero
mismatches**: an element exposed from a plain module rather than a package is `internal`, and
an element whose documentation carries the provisional notice is `provisional`. Everything
else exposed at a package level is `public`. The manifest's Python half therefore holds no
information the code does not already carry — it exists to be diffed against the thing it
duplicates.

Separately, the contract asserts that version increments carry compatibility promises, but
nothing verifies that assertion. The existing check compares the *declared* surface to the
*real* surface; no check compares this release's surface to the previous one. A `public`
element could be removed outright in a patch and every gate would pass.

## What Changes

- The stability tier of an importable element is **derived from the source** rather than
  restated in a manifest. The derivation rules become part of the contract, not an
  implementation detail of the checker.
- `[tool.spoc.stability]` retains only what cannot be derived from Python source: the twelve
  non-import elements (executable command, entry point, optional dependency groups, pytest
  fixtures, configuration schema, template set) and the `excluded` aspect flags. The 132
  Python name entries are deleted.
- Adding an importable name to the public surface stops being a four-place edit (definition,
  package re-export, `__all__`, manifest) and becomes a two-place one — the two that PEP 8
  and the documentation toolchain already require.
- The surface check's role narrows and sharpens: it stops diffing a manifest against the
  source it was copied from, and instead verifies the derivation rules hold, covers the
  non-import elements, and continues to report unobservable kinds as unverifiable.
- **New capability:** the project gains a check that compares the current surface against the
  previously released one and fails on an incompatible change, so the compatibility promise a
  version increment asserts is enforced rather than merely stated.
- Not breaking for consumers: every element keeps the tier it has today. The change is to
  where the tier is written, not to what it is.

## Capabilities

### New Capabilities

None. Both changes land inside capabilities that already exist.

### Modified Capabilities

- `public-api-surface`:
  - *Every surface element has exactly one tier* — the tier assignment gains stated rules for
    importable elements, so a tier is a consequence of how an element is exposed and
    documented rather than a separate declaration.
  - *The tier is visible where the element is defined* — currently satisfied only for
    `provisional`. It becomes true for all three tiers, which is the point of the change.
  - *The declared surface is verifiable against the real surface* — for importable elements
    the declaration and the surface become the same artifact, so divergence between them is
    no longer possible and the requirement must say what is verified instead: that the
    derivation is well-formed and that every element still resolves to exactly one tier.
    Divergence remains meaningful, and still MUST fail, for the non-import elements.

- `release-policy`:
  - *Version increments assert compatibility* — gains the requirement that the assertion is
    checkable against the previously released surface, not merely declared.
  - *A public element is withdrawn through a deprecation lifecycle* — gains enforcement: a
    `public` element that disappears without having completed the lifecycle is detectable
    before the release is published.

### Critical concerns deferred to `/ai:decide`

- **Cross-release breaking-change detection** — comparing two snapshots of a Python API and
  classifying the differences as compatible or breaking. Correctness-sensitive: a detector
  that misses a breakage converts the release policy into decoration, and one that cries wolf
  gets disabled. Mature options exist in this ecosystem and at least one is already an
  indirect dependency of the current checker; the choice is recorded before implementation.
- **Static tier derivation from source** — deciding, without importing the package, which
  module exposes a name and whether that module is a package. The existing checker already
  resolves this concern with an adopted library; the decision is whether that adoption
  extends to the derivation or whether the derivation needs its own answer.

## Impact

- **Affected configuration**: `pyproject.toml` — `[tool.spoc.stability]` drops from 212 lines
  to roughly 28. The section stops being the tier's home for importable names and becomes the
  home only for elements no static observer can see.
- **Affected tooling**: `scripts/py/tools/apicheck/` — `manifest.py` no longer reads Python
  names; `extract.py` gains package-versus-module discrimination; `core.py`'s comparison
  changes shape from set-difference to rule verification. The tool gets smaller.
- **Affected validation**: `.canon/checks.md`, `Taskfile.yml`, and `.github/workflows/ci.yml`
  all gain the cross-release check and must stay derived from the same table — the three-way
  rule in `.canon/checks.md` applies.
- **Affected docs**: `docs/docs/api/stability.md` documents the manifest as the place tiers
  are declared. That becomes wrong the moment this lands, and is part of this change set.
- **Affected process**: tier assignment stops being an explicit reviewable act in a diff. The
  cross-release check is what replaces that gate, which is why the two halves ship together
  rather than separately.
- **No runtime impact**: `src/spoc` gains and loses nothing. Zero runtime dependencies is
  unaffected — every tool involved is a development-time gate.
