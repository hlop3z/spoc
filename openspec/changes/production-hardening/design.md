# Design — production-hardening

## Context

The kernel is clean but carries five liabilities that block "infrastructure"
status: a boot that mutates `sys.path[0]` and the filesystem, a sync-only
lifecycle, an undefined concurrency story, a registry that silently substitutes
identities, and a hardcoded mode taxonomy. Packaging adds three more: a 3.13
floor, an unrelated formats toolkit inside the kernel distribution, and an
untagged version. Greenfield status (no users) means every fix can be a clean
break — no shims, no deprecation lanes.

## Goals / Non-Goals

**Goals:**

- Boot with zero process-global side effects beyond Python's module cache.
- An async lifecycle path that awaits coroutine hooks and module init/teardown.
- A stated, tested concurrency contract for the registry and the lifecycle.
- Loud identity divergence; honest restart semantics.
- Config-declarable mode sets; Python ≥3.12; `spoc-formats` as its own
  distribution in a uv workspace.

**Non-Goals:**

- Hot reload or module re-execution across restarts (`sys.modules` is never
  touched — that is now the documented contract, not a bug).
- Async ready callbacks (they are registry reads; sync stays).
- Multi-framework isolation beyond what the import-model fix already provides.
- Any behavior change in the formats capability itself.
- Free-threading (no-GIL) certification; the contract targets the GIL build.

## Decisions

### D1 — Apps are dotted module paths; `paths.py` is deleted

An app entry in `[spoc.apps]` is a dotted path (`apps.blog`,
`mycompany.platform.auth`) imported via `importlib.import_module` exactly as
written. The kernel never inserts into `sys.path` and never creates
directories; if the path does not import, start fails with `AppNotFoundError`
naming it. The namespace segment is the path's final component, validated
against the grammar at app-registration time and passed *explicitly* down to
`Loader.register` and `discover` — namespace is no longer parsed back out of
module names anywhere. The scaffold emits an `apps/` **package**
(`__init__.py`) and declares `apps.blog`, which imports because Python puts
the entry-point script's directory on the path — the kernel needs no opinion.

*Alternative rejected:* keeping `sys.path` injection behind a flag — a
footgun with a toggle is still a footgun, and stdlib shadowing is silent data
corruption territory.

### D2 — Async lifecycle: `astart()`/`ashutdown()` on stdlib asyncio

Two coroutine methods mirror `start()`/`shutdown()`. Boot phases that are pure
computation (config, app registration, discovery, ready callbacks) stay
synchronous and shared; only hook dispatch and module `initialize`/`teardown`
fork into sync/async variants (`Loader.initialize`/`ainitialize`,
`shutdown`/`ashutdown`). Coroutine-ness is detected with
`inspect.iscoroutinefunction`. The sync path, on meeting a coroutine hook,
raises `SpocError` naming the hook and pointing at `astart()` — it never
skips, never spins up a loop of its own (`asyncio.run` inside a running loop
is a crash, and guessing is worse than refusing). Build-vs-adopt: stdlib
`asyncio`/`inspect` only — the zero-dependency invariant rules out `anyio`,
and the kernel awaits, it does not schedule.

*Alternative rejected:* a single `start()` that detects a running loop and
returns a coroutine — dual-return-type APIs poison every caller downstream.

### D3 — Concurrency contract: two stdlib locks, stated scope

- **Registry:** one `threading.Lock` guards `add()` (check-then-insert made
  atomic) and snapshot creation in the read methods (`all`, `by_kind`,
  `by_namespace`, `namespaces`, `resolve`'s failure scans). Post-boot reads
  are lock-cheap and correct; during boot they see only complete records.
- **Framework:** one non-reentrant `threading.Lock` serializes
  start/shutdown transitions. Sync paths acquire blocking for the duration of
  the transition; `astart`/`ashutdown` acquire **non-blocking** and raise the
  already-started/transition-in-progress error on contention — blocking an
  event loop on a thread lock is never acceptable.
- **Contract (documented in both docstrings and docs):** declaration-time
  decorator use is thread-safe (it only sets an attribute on the target);
  transitions are serialized; reads after a completed start need no
  coordination. Tested with a thread-pool suite (racing starts, parallel
  registration, racing duplicate identifiers).

Build-vs-adopt: stdlib `threading` — a lock is not a concern one adopts a
framework for.

### D4 — Restart honesty is a documentation + test change

`shutdown()` keeps resetting what the kernel owns (registry, loader, config).
The "clean boot" sentence is replaced by the true contract: Python's module
cache and module-level state persist; module-level code runs at most once per
process; a second start re-runs discovery against cached modules. A test pins
this with an import-time counter. *Alternative rejected:* evicting app modules
from `sys.modules` — other references survive eviction, producing two live
copies of one class; that is strictly worse than honesty.

### D5 — Identity divergence raises `IdentityDivergenceError`

In `Registry.add`, an object with a prior identifier returns the existing
record only when the newly composed identifier equals it; otherwise a new
`IdentityDivergenceError` (child of `SpocError`) names both identifiers. The
first-wins silent substitution is deleted.

### D6 — Mode sets merge over the default triple

A new `[spoc.modes]` table maps mode name → cascade list
(`test = ["test", "production"]`). The effective mode set is the default
triple **merged** with declared entries (declared wins on collision), so
adding `test` never forces restating `development`. Validation: every cascade
entry and every `[spoc.apps]` key must name a mode in the effective set;
`modes` joins the closed-key validation in `config.py` as
`dict[str, list[str]]`. `_MODE_CASCADE` moves from a module constant to the
default value of this config concern.

### D7 — Floor drops to 3.12

`requires-python = ">=3.12"`, classifier and `ruff target-version` follow.
Nothing in the source needs 3.13 (PEP 695 `type` aliases are 3.12). Verified
by running the suite under a uv-managed 3.12 interpreter in addition to the
local 3.14.

### D8 — `spoc-formats` becomes a workspace member

Repo becomes a uv workspace: root distribution `spoc` (kernel + scaffold),
new member `packages/spoc-formats/` owning package `spoc_formats` (import
`import spoc_formats`), its extras (`yaml`, `xml`, `toml`, `query`, `full`),
its tests, and its own version (starts at 0.5.0 in lockstep, versioned
independently after). The kernel's `pyproject.toml` loses the extras; the dev
group depends on `spoc-formats[full]` via `[tool.uv.sources]` workspace
reference so one `uv sync` still builds the whole suite's environment.
Release workflow builds and publishes both distributions. Build-vs-adopt:
uv workspaces over a second repo — one history, one CI, two artifacts;
matches `.canon` rule 10 (one workspace package per bounded context).

### Decision: Async lifecycle execution — Adopt stdlib `asyncio` + `inspect`

- **Status**: approved
- **Why**: The kernel only awaits hooks sequentially — it never schedules,
  cancels, or runs task groups — and `dependencies = []` is a package
  invariant, which excludes any third-party runtime import.
- **Considered**: anyio (mature, Trio-style structured concurrency, backend-
  agnostic — but a runtime dependency the kernel's invariant forbids, buying
  scheduling features the kernel deliberately does not have); a sync-only
  lifecycle with user-side bridging (pushes an event-loop problem onto every
  adopter — rejected).
- **Isolation**: `Loader.ainitialize`/`ashutdown` and
  `Framework.astart`/`ashutdown` are the only async-aware code; the registry
  and declaration layers never import `asyncio`.

### Decision: Concurrency primitive — Adopt stdlib `threading.Lock`

- **Status**: approved
- **Why**: The contract is mutual exclusion on two small critical sections
  (registry writes, lifecycle transitions); a lock is a language primitive,
  not a concern one adds a dependency for.
- **Considered**: lock-free reads via copy-on-write snapshots (more machinery
  than the boot-time write pattern justifies); no locks + documented
  single-threaded boot (unverifiable by tests, contradicts the contract the
  change exists to state).
- **Isolation**: one private lock inside `Registry`, one inside `Framework`;
  neither appears in any signature or public surface.

### Decision: Multi-distribution packaging — Adopt uv workspaces

- **Status**: approved
- **Why**: Extends the already-approved "Adopt uv" ADR (DECISIONS.md), which
  chose uv explicitly for workspace coverage: one repo, one lockfile, one CI,
  two published artifacts (`spoc`, `spoc-formats`).
- **Considered**: a second repository (two histories and two CIs for one
  team, cross-repo version coordination — rejected); keeping formats in the
  kernel distribution behind extras (the cohesion defect this change removes).
- **Isolation**: workspace membership lives in the two `pyproject.toml`
  files; neither package imports the other — the kernel↔formats import
  boundary stays absolute.

## Risks / Trade-offs

- [Sync users with async hooks hit a hard error] → the error names the hook
  and the fix (`astart`); this is the loud-over-lucky trade the canon prefers.
- [Non-blocking lock in `astart` turns a legitimate concurrent-start wait
  into an error] → concurrent transitions on one framework object are a
  programming error; failing fast beats deadlocking an event loop.
- [3.12 floor claims] → CI matrix runs 3.12/3.13/3.14; the claim is only as
  good as the matrix, so the matrix changes in the same commit.
- [Two-distribution release] → `release.yml` gains a second build/publish
  step; a partial publish (kernel out, formats missing) is mitigated by
  building both before publishing either.
- [Locks add overhead to registry reads during boot] → boot-time cost only;
  post-boot reads take an uncontended lock (nanoseconds) and remain O(n).

## Migration Plan

Greenfield: no compatibility shims. The scaffold, examples, docs, and
CHANGELOG all move in this change set (canon rule 8). Existing generated
projects (none known) would re-run `spoc init`.

## Open Questions

None — the three build-vs-adopt calls (async runtime, concurrency primitive,
workspace mechanism) are recorded in `DECISIONS.md` via /ai:decide.
