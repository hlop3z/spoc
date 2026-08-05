# Error Doctrine and Hook Contract

## Why

Three contracts observable to every framework author are wrong or undefined today, and
`v0.5.0` is still untagged — each is a trivial fix now and a breaking change the moment
someone writes an `except` block, a hook, or a plugin lookup against the current
behavior. All three were findings of the production-readiness review that the
production-hardening change deliberately deferred.

1. The documented error doctrine says failures authored by app code propagate as
   themselves ("the author needs their traceback, not a wrapper around it"), but every
   lifecycle phase wraps them in the kernel's base error with the message flattened to a
   string.
2. Startup/shutdown hooks receive their kind's components as an unordered set, so any
   hook that registers routes, commands, or pages does so in nondeterministic order —
   while the loader everywhere else guarantees deterministic ordering.
3. A plugin's namespace is derived from the top-level package of its reference, so under
   dotted app paths a plugin living in `apps.blog` gets namespace `apps` — colliding
   across apps and diverging from the grammar discovery uses.

## What Changes

- **BREAKING** Lifecycle phases stop wrapping app-authored exceptions: a hook, module
  `initialize`, or `teardown` that raises propagates its own exception (rollback still
  runs). Kernel-authored failures remain kernel errors. The blanket "Error during
  startup/shutdown" wrapper is removed.
- **BREAKING** Startup and shutdown hooks receive their kind's components as an
  immutable, deterministically ordered sequence (registration order) instead of an
  unordered set.
- **BREAKING** A plugin reference's namespace is derived by the same grammar discovery
  uses — the reference reads `<app_path>.<module>.<attribute>` and the namespace is the
  final segment of `<app_path>` — instead of the reference's top-level package. A
  top-level module remains its own namespace. Two-segment references (the common
  third-party shape) are unaffected.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `framework-lifecycle`: adds the app-error propagation requirement (app-authored
  lifecycle failures surface unwrapped) and the deterministic hook-payload requirement
  (ordered, immutable component sequence).
- `project-configuration`: the "Plugins are configured registrations" requirement
  changes its namespace-derivation rule from "top-level package" to discovery's
  grammar (final segment of the app path within the reference).

## Impact

- `src/spoc/core/loader.py` — remove the four wrap sites; hook payload type.
- `src/spoc/framework.py` — `_components_for` ordering; `_register_plugins` namespace
  derivation.
- `src/spoc/core/declaration.py` — hook signature annotations on `KindSpec`.
- Tests pinning the wrapped error (`tests/test_loader.py`), hook payloads
  (`tests/test_loader.py`, `tests/test_framework.py`, `tests/test_async_lifecycle.py`),
  and plugin identity (`tests/test_framework.py`).
- Docs stating the hook payload, error doctrine, and plugin identity
  (`docs/docs/advanced/plugins.md`, `docs/docs/advanced/lifecycle.md`,
  `docs/docs/core/loader.md`, `docs/docs/core/framework.md`,
  `docs/docs/getting-started/configuration.md`), the example project, and the
  CHANGELOG (0.5.0 is untagged, so these fold into its existing section).
- No dependency or distribution changes; `spoc-formats` untouched.
