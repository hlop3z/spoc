## 1. Set up the adopted tooling

Decisions are settled — see the ADRs in `design.md`. Adopt `griffe` for extraction, extend
PEP 702 for the deprecation signal, stdlib `tomllib` for the manifest.

- [x] 1.1 `/ai:decide` — ADRs recorded in `design.md` for surface extraction, deprecation
      signal, and manifest parsing
- [x] 1.2 Add `griffe` as a development dependency only, and confirm `dependencies = []`
      is unchanged in `pyproject.toml`
- [x] 1.3 Verify `griffe check` runs against this repo and classifies a deliberately
      introduced breaking change, before building anything on top of it

## 2. Audit the surface and assign tiers

- [x] 2.1 Enumerate every element of the published surface: top-level `spoc` names,
      `spoc.formats`, `spoc.testing`, `spoc.diagnostics`, `spoc.scaffold`, the `spoc`
      console script and its machine-readable output, the `pytest11` entry point, the
      `yaml`/`xml`/`toml`/`query`/`full` extras, the `spoc.toml` schema, and the scaffold
      template contract
- [x] 2.2 Audit `spoc.core`: for each name, promote to a public location only where the
      reference application or scaffold templates need it today; otherwise confirm
      internal. Record the promotions
- [x] 2.3 Resolve the design's open question on the scaffold template contract
      (`public` vs `provisional`) using the same evidence rule
- [x] 2.4 Assign exactly one tier to every enumerated element; nothing left untiered

## 3. Write the manifest

- [x] 3.1 Add `[tool.spoc.stability]` to `pyproject.toml` with one array per tier
- [x] 3.2 Record the enumerated exclusions (message text, prose command output, pinned
      versions inside an extra, internal attributes) in the same table
- [x] 3.3 Apply any re-exports that task 2.2 identified, and replace the `spoc.core` hedge
      in the `spoc/__init__.py` module docstring with the `internal` decision

## 4. Build the drift checker

- [x] 4.1 Create the tool in `scripts/py/` via `/ai:tool`
- [x] 4.2 Implement the pure diff core: declared manifest + observed surface → undeclared,
      declared-but-absent, and unmarked-provisional findings. No I/O, no introspection
- [x] 4.3 Implement the adapters: `tomllib` manifest reader, `griffe` surface extractor
      (behind the boundary so it stays swappable), and reporter
- [x] 4.3a Implement the complement adapters for what griffe cannot see — entry points via
      `importlib.metadata`, extras and the console script via the `pyproject.toml` reader —
      feeding the same diff core
- [x] 4.4 Implement the thin entry point: argument parsing and exit code only
- [x] 4.5 Add unit tests for the diff core covering each finding type and the conformant case
- [x] 4.6 Verify the check passes against the working tree, then verify it fails on an
      injected undeclared element and on a declared-but-absent element

## 5. Mark provisional elements and build the deprecation signal

- [x] 5.1 Add the "may change incompatibly in a minor release" warning to each
      `provisional` element's documentation
- [x] 5.2 Confirm the checker reports an unmarked `provisional` element as a failure
- [x] 5.3 Add the deprecation adapter: `warnings.deprecated` on 3.13+, with a stdlib-only
      fallback for 3.12, behind a single import site. Confirm `dependencies = []` holds
- [x] 5.4 Verify the signal on both paths — it raises `DeprecationWarning`, names the
      element and its replacement, and is suppressible and escalatable via warning filters
- [x] 5.5 Exercise the lifecycle end to end on one real element — **relocated, not done.**
      Nothing in the surface warrants deprecation today, and inventing one to tick a box
      would be worse than leaving it unticked. The machinery is implemented and covered by
      19 tests across both interpreter paths; what remains is a genuine first deprecation.
      That requirement now has one canonical home — the unchecked 1.0 criterion in
      `docs/docs/api/stability.md`, mirrored by the `release-policy` spec — where it gates
      1.0 rather than this change. Tracking it in two places would be the duplication the
      canon warns about.

## 6. Publish the policy

- [x] 6.1 Write the stability and versioning docs page: the three tiers and their
      guarantees, the exclusions, the pre-stable allowance and its end condition, the
      deprecation lifecycle, and the 1.0 criteria
- [x] 6.2 Add the page to `mkdocs.yml` navigation and link it from `README.md`
- [x] 6.3 Add a `CHANGELOG.md` entry recording the policy and stating plainly that it
      supersedes the 0.5.0 "no migration path, none planned" stance going forward only,
      granting nothing retroactively
- [x] 6.4 Confirm the `Development Status` classifier matches the policy in force
      (pre-stable while the allowance stands)

## 7. Wire in and verify

- [x] 7.1 Add the surface check to `.canon/checks.md` so it runs in the same gate as tests
      and lint
- [x] 7.1a Promote the griffe ADR into `DECISIONS.md` alongside tokei — it becomes a
      durable project-wide `checks.md` tool, and archiving this change would otherwise
      bury the decision
- [x] 7.2 Draw the contract-and-projection flow as a Mermaid diagram in
      `docs/architecture/` (Rule 1)
- [x] 7.3 Run every check in `.canon/checks.md` and report anything that could not be run
      as unverified (Rule 6)
- [x] 7.4 Verify every docs snippet added in task 6 actually runs
