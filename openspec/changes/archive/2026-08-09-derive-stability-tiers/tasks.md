## 1. Record the build-vs-adopt decisions

- [x] 1.1 Run `/ai:decide` for **cross-release breaking-change detection** — recorded in `design.md` under `## Decisions (ADRs)` as Adopt `griffe check`
- [x] 1.2 Run `/ai:decide` for **static tier derivation** — recorded as Extend the existing `griffe` adoption
- [x] 1.3 Resolve where the cross-release check lives — its own gate row, not inside `apicheck`; recorded as a design decision
- [x] 1.4 Confirm the adopted tool is reachable — `griffe 2.1.0` is already a declared dependency of `apicheck` and `griffe check` runs against `v0.5.0`, so no `ensure` recipe is needed

## 2. Teach the checker the derivation rules (manifest still in place)

- [x] 2.1 Add the tier vocabulary's derivation rule to `apicheck.core` as a pure function over (exposed-from-package, carries-notice) — no I/O, no griffe import
- [x] 2.2 Extend the `extract` adapter to report, per exposed name, whether the exposing module is a package and what documentation the name carries
- [x] 2.3 Add a rule-resolution failure path: an element matching no rule, or resolving ambiguously, fails and is named
- [x] 2.4 Wire the workshop tools' test suites into a gate — discovered mid-apply that `apicheck`'s 17 tests have never been run by `task check` or CI, so every test this change adds would be dead on arrival. Added a `Tool tests` row to `.canon/checks.md`, `test:tools` to `Taskfile.yml` (and to `check`), and a step to CI
- [x] 2.5 Add a test asserting the derivation reproduces every entry of the current `[tool.spoc.stability]` Python set exactly — 132 names, zero mismatches, zero missing, zero extra
- [x] 2.6 Confirm `task check` is still green with both the manifest and the derivation present — 625 root tests, 29 tool tests, apicheck 0 fatal

## 3. Delete the restatement

- [x] 3.1 Remove the 132 Python name entries from `[tool.spoc.stability]`, keeping the 12 non-import elements and the `excluded` flags
- [x] 3.2 Narrow `manifest.py` to reading declared non-import elements only
- [x] 3.3 Rewrite the comparison in `core.py`: rule verification for governed elements, divergence-in-both-directions for declared ones
- [x] 3.4 Keep the coverage-gap reporting intact — unobserved kinds still report `unverifiable`, never absent, and the count still appears in the output
- [x] 3.5 Update the test from 2.4 to assert against the derivation as the source of truth rather than the deleted manifest entries
- [x] 3.6 Verify `apicheck` still names the undeclared and the missing for non-import elements, with a test for each direction

## 4. Add the cross-release check

- [x] 4.1 Wire the adopted comparison against the last release tag, resolving `v0.5.0` as the current baseline
- [x] 4.2 Make it report every difference classified compatible or incompatible, and report newly exposed `public` and `provisional` elements as additions
- [x] 4.3 Bind the failure condition to the increment claimed and the maturity in force — reporting only while the pre-1.0 allowance holds, failing at 1.0
- [x] 4.4 Make a missing or unresolvable baseline distinguishable from "no changes found", never silently passing
- [x] 4.5 Add a test for the removed-public-element case and the newly-exposed-element case
- [x] 4.6 Recorded the breakage in CHANGELOG.md under [Unreleased]/Removed, per Keep a Changelog and the release-policy requirement that every surface change is recorded. Was: — `TemplateSource.available` removed since `v0.5.0`, permitted by the pre-1.0 allowance but unrecorded — so the gate's first run does not report a finding with no matching record

## 5. Wire it into validation

- [x] 5.1 Add the cross-release row to `.canon/checks.md` with its command and the reason it is shaped that way
- [x] 5.2 Add the matching task to `Taskfile.yml` and include it in `check`
- [x] 5.3 Add the matching step to `.github/workflows/ci.yml` with `fetch-depth: 0` and tags, since the adopted tool resolves its baseline from the latest tag and a shallow checkout has none
- [x] 5.4 Confirm all three agree — a row that disagrees with the Taskfile is a defect in the Taskfile

## 6. Documentation

- [x] 6.1 Rewrite `docs/docs/api/stability.md` where it describes the manifest as the place tiers are declared — state the derivation rules and what remains declared
- [x] 6.2 Document how to make a name public, and how to make one provisional, in the two edits it now takes
- [x] 6.3 Execute every changed snippet on the page rather than eyeballing it for stale symbols
- [x] 6.4 Run `mdlinks` and fix anything the doc rewrite broke

## 7. Validate and close out

- [x] 7.1 Ran every row in `.canon/checks.md`. All ten gates pass. Nothing was unverified; the one `unverifiable` finding is `schema:config/spoc.toml`, pre-existing and by design
- [x] 7.2 Confirmed: 132 declared on `main`, 132 derived on HEAD, zero elements whose tier changed
- [x] 7.3 Review the full diff and split commits by intent, Conventional Commits, no co-author (Rule 3)
- [x] 7.4 Run `/opsx:sync` to fold the delta specs into `public-api-surface` and `release-policy`
- [x] 7.5 Archive with `openspec archive -y --skip-specs`, since sync already applied the specs
