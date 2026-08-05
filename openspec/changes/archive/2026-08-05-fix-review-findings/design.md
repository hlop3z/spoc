# Design — fix-review-findings

## Context

A 2026-08-05 full-source review found ~25 findings sharing one root pattern: documented
contracts stronger than the code. The architecture is sound (pure core, adapters at the
boundary, one flat registry); every fix lands inside the existing structure. No new
modules, no new dependencies, no boundary moves.

## Goals / Non-Goals

**Goals:**

- Make every documented contract true in code: loud failure where behavior was silently
  wrong, contained failure where third-party or raw exceptions escaped a declared family.
- Close the exported-but-untested surface (`Config`, `echo`, scaffold CLI argv, public
  circular-dependency path).
- Repo hygiene: Taskfile, CHANGELOG link, HANDOFF, stray files.

**Non-Goals:**

- No new capabilities, no API additions beyond the one rename.
- No re-litigating architecture (kernel/formats/scaffold boundaries stay exactly as-is).
- No back-compat shims — greenfield mandate stands; the `Identifier` rename is a clean
  break.
- No async re-design of `astart` discovery I/O; we document the contract, not change it.

## Decisions

### D1 — Reentrancy: detect and refuse, don't support

`threading.Lock` stays (not `RLock`). Supporting reentrant lifecycle transitions would
make hook-time `shutdown()` a real code path with undefined semantics mid-boot. Instead,
record the transition-owning thread; a lifecycle call from that thread while a transition
is in flight raises `SpocError` with a message naming the reentrant call. The async path
already fails loudly via non-blocking acquire; this makes sync and async symmetric.
*Alternative rejected:* `RLock` — would let `shutdown()` proceed inside `start()` and
corrupt half-booted state.

### D2 — Imported instances: the second claim is loud, not silent

`declaration.py`'s re-export filter checks `__module__` for classes/functions only. An
instance has no `__module__` of its own, and the object-identity spec forbids inferring
anything from the execution environment (stack inspection), so ownership cannot be
recorded at mark time. Instead, **layout separates a use from a claim** — the same
principle the existing kind/location check rests on:

- The object appears in a location declaring a *different* kind (`from .models import
  repo` inside `views.py`): an ordinary import, skipped silently. This is the common
  case and has to stay free.
- Two locations of the *same* kind both hold it: an ambiguous claim. The identity this
  location would assign is compared against the recorded one, and a difference raises
  `IdentityDivergenceError` naming both — instead of load order silently deciding the
  namespace.

Classes and functions keep today's `__module__` ownership skip, so re-exporting them
stays legal and silent everywhere. *Alternatives rejected:* frame capture at mark time
(violates the object-identity spec's no-stack-inspection rule); first-wins with a
warning (silent-wrong is the defect being fixed); refusing every second sighting
regardless of kind — this was the first implementation and it broke ordinary
cross-module imports inside one app.

### D3 — Closed `[spoc]` key set: reject unknown keys at load

`_SPOC_TYPES` is already the single source of the valid key set; enforcement is a
set-difference check in the config adapter with all offenders reported in one
`ConfigurationError` (matching the existing all-errors-reported style of mode
validation). Docstring count fixed as part of the same edit.

### D4 — Default isolation: deep-copy at the adapter boundary

`load_spoc_toml`/`_build_config` return structures built with `copy.deepcopy` of the
module-level defaults before merge. Defaults are small (two dicts, three short lists);
deep copy cost is nil at boot frequency. *Alternative rejected:* frozen/immutable default
types — more machinery than the problem warrants.

### D5 — Formats containment: translate at the surface, not inside codecs

`FormatError` containment is enforced where third-party control flow enters:
`access.pointer`/`access.query` wrap engine parse errors into the existing
`FormatError` subclasses; `codecs` encoder paths wrap serializer exceptions naming the
format and the offending type. The RFC-suppression drift guard is a test that asserts
the overridden attribute set equals the engine's actual extension surface, so an
upgrade fails the suite instead of silently widening syntax. *Alternative rejected:*
pinning `python-jsonpath` with an upper bound — contradicts the zero-runtime-deps
posture (it's an extra) and hides drift instead of detecting it.

### D6 — `collect` ignore mechanism: hidden-by-default plus explicit patterns

Directories (and files) whose name starts with `.` are skipped by default. An
`ignore=(glob, ...)` parameter extends the skip set; skipping is by directory/file name
match before key derivation, so grammar validation only ever sees entries that will be
collected. Loudness is preserved: a *collected* key that violates the grammar still
fails the whole collection. *Alternative rejected:* collect-what-you-can with warnings —
breaks the "eager, fails as a whole" requirement.

### D7 — Scaffold resources: `importlib.resources` end to end

Built-in template root and entry-point package targets both resolve through
`importlib.resources.files()` + `as_file()` (context-managed extraction for
non-directory installs). The pure layer gains backslash and drive-letter rejection in
`_reject_escape` (string-level checks — the pure layer stays filesystem-free); the sink's
`resolve()`/`is_relative_to` check remains as defense in depth.

### D8 — `Identifier.name` → `Identifier.object_name`

One breaking rename, applied everywhere in the same change set (kernel, tests, docs).
Greenfield mandate: no alias, no deprecation window.

### Build-vs-adopt

No new critical concerns; nothing to run through /ai:decide. All fixes extend existing
in-repo code. The only third-party surfaces touched (`python-jsonpath`,
`importlib.resources`) are already-adopted dependencies used more correctly.

## Risks / Trade-offs

- [Closed `[spoc]` key set breaks projects with stray keys] → Greenfield; loud-with-names
  error is the point. Valid keys listed in the message.
- [Hidden-by-default skip in `collect` changes existing collections that relied on
  dotted directories] → No such usage exists (greenfield); behavior documented in the
  spec delta and CHANGELOG.
- [Owner-module capture at mark time may not cover objects marked manually without the
  registrar] → The manual path already bypasses other conveniences; spec covers only the
  registrar path, and discovery falls back to current class/function behavior otherwise.
- [Drift-guard test couples the suite to `python-jsonpath` internals] → That coupling
  already exists in `access.py`; the test makes it visible instead of silent.
- [Reentrancy detection adds a thread-identity field to Framework] → Trivial state,
  cleared with `_reset()`; documented in the concurrency contract docstring.

## Migration Plan

Single change set; no data, no deploy. `Identifier.name` → `object_name` is the only
consumer-visible break and lands with docs/tests in the same commits. Rollback is
`git revert`.

## Open Questions

None — all decisions taken above.
