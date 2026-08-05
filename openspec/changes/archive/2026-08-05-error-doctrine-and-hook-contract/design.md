# Design — Error Doctrine and Hook Contract

## Context

Three deferred production-readiness findings, all observable contracts, all cheapest to
fix while 0.5.0 is untagged. The kernel already documents the intended error doctrine
(`core/exceptions.py` module docstring, `docs/core/loader.md`) — the loader just
violates it. The loader already guarantees deterministic module ordering — the hook
payload just discards it. Discovery already has one identity grammar — plugin
registration just uses a different one.

## Goals / Non-Goals

**Goals:**

- Make the documented error doctrine true in the four lifecycle phases.
- Give hooks a deterministic, immutable payload.
- Make plugin identity follow discovery's grammar, so the `_register_plugins`
  docstring's existing claim ("identity follows the same grammar as discovery")
  becomes accurate.

**Non-Goals:**

- No new config surface (no explicit `namespace =` override for plugins; derivation
  stays automatic per the automate-mechanical-transforms principle).
- No change to kernel-authored errors, rollback semantics, ordering, or the
  `spoc-formats` package.
- Not addressing the remaining deferred findings (SECURITY.md, `ty` ignore).

## Decisions

### D1: Remove the lifecycle wrap by deleting the try/except entirely

The four phases (`initialize`/`ainitialize`/`shutdown`/`ashutdown` in
`core/loader.py`) each carry
`except (CircularDependencyError, SpocError): raise` + `except Exception: raise
SpocError(...)`. Every kernel-authored failure inside these phases already raises a
`SpocError` subclass directly, so the re-raise arm is dead once the wrap arm is gone —
delete both. Pure deletion (~24 lines), no replacement mechanism.
**Alternative rejected:** narrowing the wrap to "kernel calls only" — there are no
kernel calls in the loop body that aren't already SpocError-raising; it would wrap
nothing.

### D2: Hook payload is a `tuple`, in the registry's enumeration order

`Framework._components_for` returns `tuple(c.object for c in
registry.by_kind(kind) if c.namespace == entry.namespace)`. `Registry.by_kind`
already documents its enumeration contract — ordered by canonical identifier — so
the payload inherits a deterministic order with no new bookkeeping and no second
ordering concept. Annotations on `KindSpec.on_startup`/`on_shutdown` and the
loader's `components_for` callbacks change to `Sequence[Any]` payloads
(`tuple[Any, ...]` at the construction site).
**Alternatives rejected:** `frozenset` (immutable but still unordered — fixes nothing);
`list` (ordered but mutable — a hook mutating it could imply registry effects that
don't exist).

### D3: Plugin namespace = discovery's grammar applied to the reference

A reference `<app-path>.<module>.<attribute>` mirrors the discovery layout
`<app>/<kind>.py` exactly, so the namespace is the segment immediately before the
module — implementation: the second-to-last segment of the reference's module path,
falling back to the sole segment for a top-level module, validated with the same
`validate_segment("namespace", ...)` apps use. Two-segment references (the common
third-party shape, `pkg.extras.hook`) derive the same namespace as before; only
deeper paths change, which is exactly where the old rule was wrong.
**Alternatives rejected:**

- *Keep top-level package*: under dotted app paths every in-project plugin lands in
  namespace `apps` — collisions across apps, and a second grammar besides discovery's.
- *Match reference against installed apps, else top package*: the same URI's identity
  would depend on the installed-app list (stateful, order-dependent — plugins register
  before apps in boot) and it still needs a fallback rule anyway.
- *Explicit namespace in config*: taxes every declaration to serve the rare ambiguous
  case; violates automate-mechanical-transforms.

### Build-vs-adopt

No external concern is touched: all three fixes are behavior changes inside the
existing zero-dependency kernel (stdlib only). Nothing to rent, adopt, extend, or
fork — no new ADR entries for `DECISIONS.md`.

## Risks / Trade-offs

- [App exceptions now escape `start()` untyped] → Documented doctrine; callers who
  want one catch-all still have it for kernel failures (`SpocError`), and their own
  exception types are their own. CHANGELOG names the removed wrapper message.
- [A hook relying on set semantics (e.g. `in` checks, set ops) breaks] → Greenfield,
  0.5.0 untagged; tuple supports `in`; CHANGELOG marks it breaking.
- [A deep third-party reference (`vendor.pkg.plugins.auth.Thing`) derives namespace
  `auth`'s parent segment rather than the distribution name] → The rule is the same
  one app authors already learned from discovery, documented with examples; any
  derivation rule fails some layout, and this one fails fewer real ones than
  top-package did.

## Migration Plan

Fold into the untagged 0.5.0 CHANGELOG section (greenfield — no shims, no
deprecation window). Docs, example project, and tests move in the same change set.
