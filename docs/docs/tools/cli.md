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

| Option       | Default          | Meaning                                      |
| ------------ | ---------------- | -------------------------------------------- |
| `--path`     | `./<name>`       | Directory to generate into                   |
| `--app`      | `core`           | Name of the starter app                      |
| `--kinds`    | `models,views`   | Kinds the framework declares                 |
| `--template` | `default`        | Template set — see [templates](#templates)   |

If anything would collide with existing files, nothing is written at all.

Every generated project also gets a `.spoc-template.json` noting which template
set produced it — whatever set you named, and whoever wrote it. Nothing reads it
at runtime — delete it and the project still starts — but `spoc app` uses it to
warn you when you're about to add an app from a different template than the rest
of the project came from.

SPOC writes that file itself. A template set cannot suppress it by leaving it
out, and cannot supply what it says: a set that declares a file landing there is
refused before anything is written. A record its own subject could author would
tell you nothing.

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

## Templates

`--template` takes four forms. Which one you mean is decided by how you spell
it, before SPOC looks at anything — so a typo is always reported as a typo,
never as a missing directory you never named.

| Form                            | Example                                     |
| ------------------------------- | ------------------------------------------- |
| An installed set's name         | `default`                                   |
| A directory                     | `./mytemplates`, `C:\templates`             |
| A GitHub repository             | `gh:owner/repo`                             |
| Any archive URL                 | `https://host/sets.tar.gz`                  |

The last two carry optional parts, spelled the way `pip` spells them:

```bash
spoc init hello --template gh:owner/repo@v1.2
spoc init hello --template gh:owner/repo@v1.2#subdirectory=templates/minimal
spoc init hello --template git+https://gitlab.com/owner/repo@v1.2
```

`@v1.2` pins a revision; `#subdirectory=` picks one set out of a repo that holds
several. If you don't pin, SPOC resolves the reference to an exact commit before
fetching, and tells you which one, so you can pin it next time:

```text
Generated from gh:owner/repo at revision 8f2c1ab….
Reproduce this exact project with:
  --template gh:owner/repo@8f2c1ab…
```

Fetched templates are cached by commit, so generating a second project from the
same reference does no network work — and still works offline.

### What a template can and cannot do

**A template set cannot run code.** SPOC substitutes named values and nothing
else: no expressions, no conditionals, no hooks, no scripts that run during
generation. This is a guarantee, not an implementation detail, and it is what
makes `--template gh:someone/repo` a reasonable thing to type — unlike
scaffolding tools that execute template-supplied hooks by design.

What you should still weigh: the *generated project* is code written by whoever
wrote the template, and you're about to run it. That's the same trust decision
as `git clone`, and no tool can make it for you.

**A template set cannot write `.spoc-template.json`.** That destination is
reserved: SPOC writes the origin record for every generation, and a manifest
declaring a file that lands there is refused, naming it. The three values that
used to feed the record — `template_reference`, `template_revision`, and
`template_set_name` — are no longer part of the substitution vocabulary, so a
set that declares one is refused as unsatisfiable. If you are writing a template
set, don't declare the record; you get it for free.

A remote reference is also the **only** thing that makes SPOC touch the network.
No other command opens a connection.

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
