# Framework Object API

## Why

Building a framework on the kernel today takes ~60 lines of boilerplate across three
declarations that must agree by hand: a `Components(...)` kind set, hand-written
decorators wrapping `register`, and a `Schema(modules=[...])` repeating the same kind
list. The duplication has already produced real drift downstream (zmag declares
`Components("models", "api")` but `Schema(modules=["models", "api", "tools",
"commands"])`, leaving two kinds that load but can never register), and the kernel
offers no post-discovery phase, so frameworks finalize cross-component state as import
side effects. Config is likewise split across two homes (`spoc.toml` and
`settings.py`), and the docs teach every variant. The intended developer experience —
one obvious, conventional way, minimal boilerplate — is not what the API delivers.

## What Changes

- **BREAKING** One `Framework` object becomes the single declaration point: the kind
  set, inter-kind dependencies, and lifecycle hooks are stated once, on it. The
  separate `Components` + `Schema` public surface is removed.
- Framework authors obtain per-kind registration decorators from the framework object
  itself; the decorators support bare and named forms without any hand-written wrapper
  code.
- **BREAKING** Construction becomes pure (no filesystem, `sys.path`, or import side
  effects). Discovery and loading happen in an explicit `start(base_dir)` step;
  `shutdown()` remains the counterpart.
- A post-discovery finalize phase (`on_ready`) fires exactly once after all components
  are registered and before the application runs — the sanctioned home for
  cross-component builds (ORM materialization, route trees, DI graphs).
- **BREAKING** `spoc.toml` becomes the only configuration source the kernel reads
  (mode, per-mode app lists, plugins). `settings.py` is no longer read, required, or
  defaulted by spoc — it remains a user-owned convention for their own constants.
- Docs are rewritten to teach exactly one conventional path (single quick-start,
  single project layout); alternative-way sections are deleted.
- The bundled example is reduced to the new surface and stays the definition-of-done
  for the intended developer experience.

## Capabilities

### New Capabilities

- `framework-declaration`: declaring a framework — the closed kind set, inter-kind
  dependencies, and per-kind registration decorators — exactly once, on one object,
  such that a second conflicting declaration point cannot exist.
- `framework-lifecycle`: the framework's phase contract — inert after construction,
  loud discovery on explicit start, a single post-discovery ready phase, ordered
  shutdown — and the failure behavior of each phase.
- `project-configuration`: the single declarative configuration surface (`spoc.toml`):
  mode selection, per-mode app cascade, plugin lists, and the guarantee that no other
  file is required or consulted by the kernel.

### Modified Capabilities

<!-- component-registry, component-resolution, and object-identity requirements are
     unchanged: the registry remains flat, resolution per-segment, identity
     kind:namespace.object_name. This change only relocates how the kind set and
     lifecycle are declared. -->

## Impact

- **Public API (breaking)**: `Components`, `Schema`, and `Hook` leave the public
  surface; `Framework.__init__` signature changes; `load_configuration` /
  `load_environment` behavior narrows to TOML-only. Registry, resolution, identifier,
  and exception surfaces are untouched.
- **Code**: `src/spoc/framework.py` (rewritten around the new object),
  `src/spoc/components.py` (internalized), `src/spoc/core/config_loader.py`
  (settings-module loading removed), `src/spoc/inject_apps.py` (moves under `start`).
- **Tests**: framework and config-loader suites rewritten to the new surface;
  registry/identifier/importer suites largely unaffected.
- **Docs**: quick-start, configuration, and lifecycle pages rewritten to the single
  conventional path; architecture diagram updated (Rule 1); API reference pages follow
  the new symbols.
- **Examples**: `examples/framework/framework.py` shrinks from ~60 lines to under 10;
  `examples/config/settings.py` reduced to user constants only.
- **Downstream**: zmag currently pins an older spoc and is unaffected until it
  upgrades; the new surface is the migration target it would move to.
