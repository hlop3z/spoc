## 1. Record the build-vs-adopt decisions

- [x] 1.1 Run `/ai:decide` for "reading the withdrawal mark without executing the package" —
      approved as **Extend griffe with a stdlib `ast` pass**, recorded in `DECISIONS.md`
- [x] 1.2 Run `/ai:decide` for "reconstructing per-release history" — approved as **Extend
      `apicheck.release`**, recorded in `DECISIONS.md`

## 2. Model withdrawal in the pure core

- [x] 2.1 Add `Withdrawal` to `core.py` — the mark's message, and whether it names a
      replacement or states there is none
- [x] 2.2 Add `withdrawal: Withdrawal | None` to `Exposure`, defaulting to `None`, leaving
      `Tier` and `derive_tier` untouched
- [x] 2.3 Add the `Finding.Kind` members for a mark with no replacement, an unsanctioned
      withdrawal signal, and an undeterminable history
- [x] 2.4 Add a pure `lifecycle_verdict(...)` taking an element's per-release presence and
      marks and returning compliant / violated / undetermined, with the reason
- [x] 2.5 Unit-test 2.4 directly against synthetic release sequences: never marked, marked
      only in the preceding release, marked with only patch releases in between, marked
      with a full minor line in between, marked at the oldest known release

## 3. Read the mark from source

- [x] 3.1 In `extract.py`, parse each source file and recognize the sanctioned mark —
      `deprecated_alias(target, message)` at module level and `@deprecated(message)` on a
      definition — recovering the message across implicitly concatenated literals
- [x] 3.2 Populate `Exposure.withdrawal` from 3.1 and assert `spoc.scaffold.extract_archive`
      comes back `public` **and** withdrawn
- [x] 3.3 Report a `DeprecationWarning` raised anywhere outside `spoc/core/deprecation.py`
      as an unsanctioned mark, naming where it is produced
- [x] 3.4 Report a mark whose message neither names a replacement nor says there is none;
      confirm the existing mark passes unchanged

## 4. Walk the published releases

- [x] 4.1 In `release.py`, enumerate tags as parsed versions, ordered by version and grouped
      into minor lines — not by creation date, and not counting tags
- [x] 4.2 Add a lazy backward walk yielding each release's presence and mark for one
      element, stopping at the first release where it is present without a mark
- [x] 4.3 Return an explicit undetermined result when the history cannot be established —
      no reachable releases, or the mark still present at the oldest one with too few minor
      lines after it
- [x] 4.4 Test 4.1–4.3 against a temporary repository with a synthetic tag sequence that
      includes patch releases within one minor line

## 5. Wire it into the comparison

- [x] 5.1 In `diffcli.py`, trigger the walk only for `REMOVED` changes where `promises` is
      true, and report each verdict
- [x] 5.2 Print withdrawal alongside the tier wherever an element is rendered, never in
      place of it
- [x] 5.3 Apply the fatality split from design: mark-content and unsanctioned-signal
      findings fatal immediately; lifecycle violations fatal from 1.0; undetermined history
      never a pass, exit `2`
- [x] 5.4 Include the undetermined count in the summary line, so a run never implies a check
      it did not perform
- [x] 5.5 Test the post-1.0 behavior directly against a synthetic declared version rather
      than waiting for 1.0

## 6. Validate and document

- [x] 6.1 Run `apicheck` and `apidiff` against this repository; confirm the existing
      withdrawal passes and no new fatal finding appears
- [x] 6.2 Run the checks in `.canon/checks.md`; report anything that could not be run as
      unverified
- [x] 6.3 Update the published stability documentation where it describes what the check
      verifies, since the set has grown (Rule 8)
- [x] 6.4 Add the `### Deprecated`-adjacent changelog entry describing the new enforcement
- [x] 6.5 Review the diff and commit split by intent, Conventional Commits, no co-author
      (Rule 3)
