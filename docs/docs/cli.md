# Command Line

The `spoc` program does five things: **init** generates a runnable project,
**app** adds an app to one, **check** validates a project before runtime,
**list** and **explain** read its registry. Everything the CLI does is a
thin adapter over a library call — `spoc.scaffold` and `spoc.diagnostics`
expose the same operations to code that never touches argv.

## `spoc init`

```console
$ spoc init myproject
$ spoc init myproject --kinds models,views --app blog
$ spoc init myproject --template ./mytemplates
```

Generates configuration, a framework declaration, one app, and an entry
point; the project runs unedited. See the
[installation guide](getting-started/installation.md) — `uvx spoc init`
works without installing anything.

`--template` takes an installed template set's name, or a directory path —
the reference is a path exactly when it contains a separator
(`./mytemplates`), so a bare name never silently resolves to a same-named
local directory.

## `spoc app`

```console
$ spoc app blog
Created apps/blog
  apps/blog/__init__.py
  apps/blog/models.py
  apps/blog/views.py

Install it: add "apps.blog" to a mode list under [spoc.apps] in config/spoc.toml
```

Generates one additional app — the same shape `init` emits, one module per
kind. The kinds come from the project's own framework declaration (no
restating what `framework.py` already says); `--kinds models,views`
overrides. An existing app is never overwritten, and your configuration is
never edited — the exact entry to add is printed.

## `spoc check`

```console
$ spoc check                # current directory
$ spoc check path/to/proj
OK: path/to/proj checks out clean
```

Dry-boots the project and reports what the first real boot would raise —
before it ships:

- configuration problems (syntax, typing, a mode absent from the cascade)
- unresolvable app and plugin references
- kind dependency cycles and identity collisions
- coroutine hooks the synchronous lifecycle would refuse (`start()` vs
  `astart()`)

Every finding carries the kernel's own message — the failing segment and the
valid candidates — and the exit code is `0` clean / `1` findings. The dry
boot is fully isolated: nothing it imports or registers outlives the command.

!!! note "check imports your apps"
    Validating the declaration means importing the app modules that carry
    it, so module-level code runs — the same truth `manage.py check`
    accepts. An exception raised by your own module code propagates
    untouched; only SPOC's typed errors become findings.

## `spoc list`

```console
$ spoc list
models:blog.post
models:shop.order

$ spoc list --kind models --namespace shop
models:shop.order
```

Boots, enumerates every registered identifier in deterministic order, tears
down. `--kind` is validated against the declared kind set (a typo names the
valid kinds); namespaces are an open set, so an unknown one is simply empty.

## `spoc explain`

```console
$ spoc explain models:blog.post
identifier:  models:blog.post
kind:        models
namespace:   blog
object_name: post
object:      blog.models:Post
```

Resolves one canonical identifier and describes the record. A typo fails
with the kernel's candidate-naming error — never an empty result.

## Locating the framework

All three diagnostics find the declaration by the convention `spoc init`
emits: a top-level `framework.py` exposing `framework`. A project shaped
differently states it explicitly:

```console
$ spoc check --framework myapp.runtime:framework
```

If neither works, the error says exactly what was searched and how to
override it.
