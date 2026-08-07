# The Command Line

Installing SPOC gives you one command, `spoc`, with five subcommands: two that
**generate** and three that **inspect**.

```text
spoc init      Generate a new project that starts unedited.
spoc app       Generate one additional app into an existing project.
spoc check     Validate the project before runtime.
spoc list      List every registered identifier.
spoc explain   Describe one registered identifier.
```

## `spoc init` — a new project

```bash
spoc init hello
```

Creates `./hello` with settings, a framework declaration, one app, and an
entry point — [the quick start](../getting-started/quick-start.md) walks
through every file. Options:

| Option       | Default          | Meaning                                  |
| ------------ | ---------------- | ---------------------------------------- |
| `--path`     | `./<name>`       | Directory to generate into               |
| `--app`      | `core`           | Name of the starter app                  |
| `--kinds`    | `models,views`   | Kinds the framework declares             |
| `--template` | `default`        | Template set (a name, or a directory)    |

If anything would collide with existing files, nothing is written at all.

## `spoc app` — one more app

```bash
spoc app blog
```

Generates `apps/blog/` with one module per kind — and it reads the kinds from
**your own `framework.py`**, so you never restate them. It won't edit your
settings; it prints the exact line to add:

```text
Install it: add "apps.blog" to a mode list under [spoc.apps] in config/spoc.toml, e.g.
  development = [..., "apps.blog"]
```

## `spoc check` — find problems before runtime

```bash
spoc check
```

```text
OK: /path/to/hello checks out clean
```

`check` does a dry boot and reports everything the first real boot would
complain about: settings typos, apps that don't import, dependency cycles,
name-tag collisions, async hooks on the sync path. Every finding uses the same
precise wording the runtime error would. Exit code `0` means clean — perfect
for CI.

!!! note
    A dry boot still *imports* your app modules. Nothing outlives the check —
    the framework is torn down and import state restored.

## `spoc list` and `spoc explain` — read the shelf

```bash
spoc list
spoc list --kind models
spoc list --namespace blog
```

```text
models:blog.post
models:core.example
```

```bash
spoc explain models:core.example
```

```text
identifier:  models:core.example
kind:        models
namespace:   core
object_name: example
object:      apps.core.models:Example
```

Both boot, read, and tear down — nothing stays running.

## Where's the framework?

The inspect commands accept a project path and, if your declaration doesn't
live at the default spot (`framework:framework`, what `init` emits), a
pointer to it:

```bash
spoc check path/to/project --framework mypkg.setup:framework
```

Next: [testing your project](testing.md).
