## Why

Every provisional element in the distribution — 27 of them — is in `spoc.scaffold`, which
exports 49 names. The kernel's surface is already committed as `public`; the scaffolder's
is entirely undecided. That makes one of the published stable-release criteria
("no element intended `public` at the stable release is still `provisional`") a question
about the scaffolder and nothing else.

The decision is free exactly once. The pre-stable allowance lets a `public` element be
withdrawn in a minor release; after 1.0 the same withdrawal costs a full deprecation
lifecycle spanning two releases. Every name currently exported is a promise that has never
been deliberately made, and un-making it never gets cheaper than it is now.

The contract also has a gap that guarantees the problem returns. `public-api-surface`
states, totally and mechanically, *how a tier follows from exposure* — but nothing states
*what may be exposed*. A surface trimmed today can regrow tomorrow with no rule broken.

## What Changes

- Every element exposed from `spoc.scaffold` is assigned an intended tier for the stable
  release: `public`, `provisional` past 1.0, or `internal`. The decision is recorded once,
  per element, with the reason it was reached.
- **BREAKING**: elements decided `internal` stop being exposed from `spoc.scaffold` and
  become reachable only from their defining submodule. Permitted in a minor release under
  the pre-stable allowance; recorded as breaking in the release's surface changes.
- Elements decided `public` lose their provisional notice. Elements that stay
  `provisional` past 1.0 keep it, and the reason they remain unsettled is stated where the
  element is defined rather than left implicit.
- The surface contract gains a requirement governing *exposure itself*, so the published
  namespace has a stated admission rule and a later addition can be judged against it.
- At least one element completes the full deprecation lifecycle rather than being
  withdrawn under the allowance, so the criterion that the lifecycle be *exercised* is met
  by evidence rather than by assertion.
- The generated documentation and the surface-delta report are brought into agreement with
  the result; a doc naming a name that is no longer exposed is a defect in this change,
  not a follow-up.

## Capabilities

### New Capabilities

None. This change decides values the existing contract already governs and closes one gap
in that contract.

### Modified Capabilities

- `public-api-surface`: add a requirement stating the condition under which an element may
  be exposed from a published namespace at all. The contract currently derives a tier from
  exposure but places no constraint on exposure, so a surface can grow without any rule
  being violated. The requirement is about admission, not about the tier rules, which are
  unchanged.

## Impact

**Affected code** — `src/spoc/scaffold/__init__.py` (the 49-name export list) and the
provisional notices in `errors.py` (7), `provenance.py` (6), `plan.py` (6), `archive.py`
(3), `remote.py` (2), `cache.py` (2), `sources.py` (1).

**Affected consumers** — none outside the repository; the kernel does not import from
`spoc.scaffold`, and that one-way dependency is already pinned by the test suite. Internal
importers are `spoc.scaffold.cli` and the scaffold test modules, which reach their
submodules directly or must be moved to.

**Affected checks** — `apicheck` re-derives every tier from the source and must stay at
zero fatal findings. `apidiff` will report a larger removal set against `v0.5.0`; it
reports without failing until 1.0, and the removals must appear in `CHANGELOG.md` under
the release's surface changes.

**Affected documentation** — any published page that imports a withdrawn name, and the
stability page insofar as it describes what the scaffolder promises.

**Not affected** — the behaviour of `spoc init` and `spoc app`, the origin record's format
and content, the kernel's surface, and the dependency footprint, which stays empty.

**Critical concerns** — none of the concerns in this change are correctness-, security-,
or reliability-sensitive in a way that admits an external tool: the surface is already
derived and verified by adopted tooling (`griffe`, via `apicheck` and `apidiff`), and what
remains is a decision per element. `/ai:decide` should confirm that assessment rather than
assume it.
