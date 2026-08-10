## Why

`release-policy` already requires that a `public` element only be withdrawn through a
deprecation lifecycle, and that the lifecycle be **enforced by the same comparison that
checks compatibility** — explicitly, that "detection MUST NOT depend on a reviewer
remembering the element existed." Nothing implements that. The surface check models tiers
and the cross-release comparison models added/removed/retiered, and neither models
withdrawal at all, so an element that has entered the lifecycle is indistinguishable from
one that has not.

The consequence is a false pass in the only direction that matters. The one element
currently being withdrawn resolves to `public` with no indication of its state, and the
release that removes it will report an ordinary removal. That release is 1.0 — the release
at which the pre-stable allowance ends and the lifecycle stops being optional — so the
first time the rule is load-bearing is the first time it goes unchecked.

Now, because the mark itself is still unreleased. The waiting period the rule measures has
not started, so the check can be in place before there is any history for it to get wrong.

## What Changes

- The surface observation gains a **withdrawal state**: for each exposed element, whether
  it has been marked for withdrawal and what the mark says. This sits **beside** the tier,
  not among the tiers — a marked element keeps the promise its tier carries until the
  release that removes it.
- The verification reports a mark that does not name a replacement, or state that there is
  none, as a finding.
- The verification reports a withdrawal signal expressed outside the project's single
  sanctioned mechanism as a finding, so an unrecognized spelling fails loudly instead of
  reading as "not deprecated."
- The cross-release comparison gains **history beyond one baseline**. Establishing that a
  removal was marked *in an earlier release*, and that a full minor release shipped in
  between with the element still functional, is a question about three points in time; the
  comparison currently holds two and cannot answer it.
- Where the comparison cannot determine an element's withdrawal history, it says so and
  does not treat the removal as justified. An undeterminable answer is reported, never
  silently read as compliant.
- Findings follow the existing pre-stable allowance: reported from the start, fatal from
  1.0, so the gate never contradicts the policy it enforces.

No change to `spoc` itself, and no change to what any consumer imports.

## Capabilities

### New Capabilities

None. The behavior this change makes real is already required by `release-policy`; what is
missing is the requirement that makes it *observable*, which belongs to the capability that
owns surface verification.

### Modified Capabilities

- `public-api-surface`: add the requirement that an element's withdrawal state is visible
  in the artifact the same way its tier is, that the verification covers it, and that an
  undeterminable withdrawal history is reported as a gap rather than passed. Today the
  capability requires every element to resolve to exactly one tier and requires coverage
  gaps to be reported — but says nothing about withdrawal, which is why a check that
  satisfies it completely can still miss the lifecycle entirely.

### Critical concerns (tool choice deferred to `/ai:decide`)

- **Reading the withdrawal mark without executing the package.** The check's no-import
  invariant is load-bearing — it audits the working tree, not whatever is installed — so
  the mark has to be recoverable statically. Correctness-sensitive: a mark the observer
  fails to recognize produces a false pass.
- **Reconstructing per-release history.** Determining what a past release exposed, and
  whether it carried the mark, is a question about published artifacts rather than the
  working tree. Correctness-sensitive for the same reason, and the unit the policy counts
  in is the minor release, not the tag.

## Impact

- `scripts/py/tools/apicheck` — the observation record, the tier derivation's siblings, the
  cross-release comparison, and both CLI adapters. Its tests grow cases for each lifecycle
  rule.
- `openspec/specs/public-api-surface/spec.md` — one added requirement.
- No change to `src/spoc/`. The existing withdrawal in `spoc.scaffold` becomes the fixture
  the new checks are exercised against, and must continue to pass unchanged.
- `docs/` — wherever the stability contract describes what the check verifies, since the
  set of things it verifies grows.
