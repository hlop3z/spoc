## Why

SPOC ships at 0.5.0 with no statement of what is public. Every symbol an import can reach
is therefore either an unwritten promise or nothing at all, and no reader — including us —
can tell which. The 0.5.0 changelog's "no migration path is provided, and none is planned"
is not a policy; it is the absence of one, which was free only while the package had no
users.

Now is the moment because the surface has stopped moving: the registry kernel, scaffolder,
formats, diagnostics, testing, and remote templates have all landed and archived. A surface
declared while it is stable and before users arrive is a decision we make; declared after
users arrive, it is a decision made for us by whatever someone happened to import.

## What Changes

- **Every importable and invocable surface gets exactly one tier**, and the tier is what
  carries the guarantee:
  - **Public** — breaking changes only in a major release, after a deprecation period.
  - **Provisional** — public and documented, but may break in a minor; must be marked as
    such at its definition and in its docs, so opting in is deliberate.
  - **Internal** — no guarantee at all; may change or vanish in a patch.
- **`spoc.core` becomes Internal**, ending today's hedge that it is "reachable for anyone
  extending the kernel." Each symbol under it is audited once: either it is genuinely
  needed by a downstream framework and gets promoted to a public location, or it is
  confirmed internal. A name reachable only through `spoc.core` carries no promise.
- **The tiering covers more than Python imports** — the `spoc` console script, the
  `pytest11` entry point, the extras (`yaml`/`xml`/`toml`/`query`/`full`), the `spoc.toml`
  schema, and the scaffold template contract are each assigned a tier, because each is a
  thing a user can depend on.
- **The contract states its own exclusions.** Exception *types and hierarchy* are public;
  their message text is not. Machine-readable CLI output is public; human-readable prose
  output is not. Pinned versions inside an extra are not public; the extra's name is.
  Absence of a promise is written down rather than inferred.
- **A deprecation lifecycle**: a Public symbol slated for removal emits a runtime
  deprecation signal, is recorded in the changelog under Deprecated, and survives at least
  one minor release before a major may remove it. Nothing is removed silently.
- **The declared surface becomes machine-checked**, so drift between the contract and the
  code is a failing check rather than a discovery made by a user. This is the change's one
  critical concern (see Capabilities).
- **BREAKING (policy, not code)** — this supersedes the 0.5.0 stance. Pre-1.0, breaking
  changes still land in minor releases; at 1.0 that licence is spent. The change also
  states the criteria that must hold before 1.0 is cut, so the version becomes a
  consequence of meeting them rather than a mood.
- The `Development Status` classifier stops being decorative and is tied to the same
  criteria.

No public behavior is removed by this change; the audit may *add* re-exports.

## Capabilities

### New Capabilities

- `public-api-surface`: which names, commands, entry points, extras, and file schemas are
  Public, Provisional, or Internal; how each tier is marked at its definition; what the
  contract explicitly does not cover; and the requirement that the declared surface and
  the real surface be verifiable against each other.
  - **Critical concern (defer the tool to `/ai:decide`)**: *surface extraction and drift
    detection*. Determining a Python package's true public API and diffing it across
    versions is a correctness-sensitive problem with mature prior art, and this repo has
    already paid once for hand-rolling a solved problem. The spec states the required
    behavior; the build-vs-adopt call is recorded before implementation.
- `release-policy`: the versioning commitment (what a major, minor, and patch each mean
  for a Public symbol), the deprecation lifecycle and its minimum durations, the changelog
  obligations that accompany each tier transition, and the explicit criteria for cutting
  1.0.

### Modified Capabilities

<!-- None. No existing spec in openspec/specs/ describes the package's distribution
     surface or its release guarantees, so this change adds rather than amends. -->

## Impact

- **Docs** — a new stability/versioning page; `README` and the `spoc/__init__.py` module
  docstring, which currently states the `spoc.core` hedge this change replaces.
- **Code** — tier markers at their definitions; any re-exports the `spoc.core` audit
  promotes; no behavior change.
- **Packaging** — `pyproject.toml` classifier, tied to the 1.0 criteria.
- **History** — `CHANGELOG.md` gains the policy and records that it supersedes the 0.5.0
  no-migration stance.
- **Validation** — a surface check joins `.canon/checks.md` so the contract is enforced by
  the same gate as everything else.
- **Dependencies** — must hold the zero-runtime-dependency mandate: any adopted tooling is
  development-time only and never enters the base install.
