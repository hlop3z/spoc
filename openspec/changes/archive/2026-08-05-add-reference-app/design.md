## Context

`examples/` already carries the mechanics: a four-kind declaration
(`models`, `views` depending on models, optional `middleware`/`hooks`),
apps across the three modes, plugins, and an HTTP projection
(`http_app.py`) that builds routes from registry records. What it lacks is
a domain, cross-namespace interaction, the async path, and any CI
exercise. FastAPI lives in the `examples` dependency group; the default
sync installs only `dev`.

## Goals / Non-Goals

**Goals:**
- Reshape the apps into a storefront: `catalog`, `orders` (resolves
  catalog through the registry at call time), `accounts`; keep the plugin
  surface.
- `async_main.py`: a declaration with coroutine `on_startup`/`on_shutdown`
  hooks over the same apps, booted with `astart`.
- `tests/test_examples.py` boots the real `examples/` tree via
  `spoc.testing.isolated` (framework passed in, tree not generated — the
  example directory is the fixture).
- CI installs `--group examples` so the FastAPI construction runs.

**Non-Goals:**
- No separate repository (one home; drift dies in CI here).
- No database, no persistence — in-memory domain data keeps the example
  about the kernel, not about an ORM.
- No template-set extraction from the example (different concern).

## Decisions

### D1 — Domain: storefront with in-memory data
`catalog` models `Product`; `orders` models `Order` and its view resolves
`models:catalog.product` through `framework.resolve` while handling a call
— the cross-namespace scenario, done the registry way rather than by
importing the other app's module. `accounts` models `UserAccount` (keeps
the stated-name example). `demo`/`other`/`another` are deleted.

### D2 — Async entry: the async declaration variant, same apps
`async_main.py` constructs the async variant of the project declaration
(coroutine `on_startup`/`on_shutdown`) and `astart`s over the same tree; a
process runs one declaration or the other. Building this surfaced a real
constraint the reference app now documents: app code that resolves at call
time binds to the project's one declaration module, so the async entry does
its cross-namespace resolution in the surface — the idiomatic place —
rather than through `orders`' view. (First candidate for the friction log
this change exists to produce.)

### D3 — Tests boot the real tree
`tests/test_examples.py` inserts `examples/` on the path inside
`spoc.testing.import_state`, imports the example's own `framework`
declaration, and boots against the examples directory — the example is the
fixture, so drift is caught against the actual files. FastAPI-dependent
tests use `pytest.importorskip`; CI installs the group so the skip never
happens there (spec scenario).

### D4 — CI: `uv sync --locked --group examples`
One flag on the existing install step. `.canon/checks.md`'s unit-test row
is unchanged (`uv run pytest`); the environment description lives with the
workflow, and the Taskfile's sync task gains the same group so `task
check` matches CI.

## Risks / Trade-offs

- [Example tests import the example's modules, which linger in
  `sys.modules`] → the suite's `import_state` scope restores everything;
  the module is opted into the shared cleanup fixture.
- [FastAPI API drift breaks the projection test] → that is the point of
  pinning; the group is version-bounded in `pyproject.toml`.
- [Deleting toy apps breaks docs referencing them] → the docs sweep is a
  task; `mdlinks` gates dead references.

## Migration Plan

Reshape in place; delete superseded apps in the same change (Rule 5). No
downstream exists.

## Open Questions

None.
