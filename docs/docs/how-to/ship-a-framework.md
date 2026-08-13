# Ship a Framework

You've built a framework on SPOC — you declared your kinds, and your users
write apps against them. This page is about the part after that: giving *your*
users the project-generation and inspection tooling you already have, without
writing any of it.

That tooling is not SPOC's alone. `init`, `app`, `check`, `list`, and `explain`
are parameterized by whatever framework declares the kinds, so a framework built
on SPOC inherits the whole line rather than rebuilding it.

!!! info "Two audiences, one page"

    [Ship a Reusable App](ship-a-reusable-app.md) is for distributing **an app**
    other projects install. This page is for distributing **a framework** other
    people build projects on.

## What your users already get

Nothing here needs shipping — it works the moment someone declares a framework:

```
spoc app billing        # one module per kind YOU declared
spoc check              # dry-boots their project, reports problems
spoc list               # what their registry holds
spoc explain models:billing.invoice
```

`spoc app` is the one worth understanding. It does not generate SPOC's kinds —
it reads the project's own `framework.py`, takes the kind set from it, and
writes one module per kind. Declare `models`, `views`, and `jobs`, and
`spoc app billing` produces:

```
billing/
├── __init__.py
├── models.py
├── views.py
└── jobs.py
```

Your vocabulary, not SPOC's. The configuration is never edited for them — the
exact `[spoc.apps]` entry to add is printed instead, so nothing rewrites a file
they own.

## Ship your project template

`spoc init` generates a project from a **template set**. Ship your own and your
users start from *your* layout — your `framework.py`, your entry point, your
conventions — instead of the generic one.

A template set is a directory holding a `manifest.toml` beside its files.
Declare it under the `spoc.scaffold_templates` entry-point group:

```toml title="pyproject.toml"
[project.entry-points."spoc.scaffold_templates"]
hello = "hello_framework.templates"
```

The value resolves to a directory path or an importable package containing the
manifest. Once your distribution is installed, the set is resolvable by bare
name:

```
spoc init acme --template hello
```

The group name is part of the published surface, and available as a constant if
you'd rather not hardcode the string:

```python
from spoc.scaffold import ENTRY_POINT_GROUP

print(ENTRY_POINT_GROUP)
#> spoc.scaffold_templates
```

Users can also point at a set you have not published at all — a directory, a
`gh:owner/repo` reference, or an archive URL. A remote reference is the only
thing that causes `spoc` to reach the network.

### What a template can and cannot do

Templates are `$name` substitution and nothing else — no expressions, no
conditionals, no evaluation. Both file *contents* and file *paths* substitute,
and every placeholder a template uses must be declared in the manifest, so a
typo fails at generation rather than shipping a file with a literal `$nmae` in
it.

That is deliberate: a template set is a layout, not a program. If you want
"include the auth module? y/n" branching, ship two sets rather than one set with
logic in it.

## Put the commands under your own name

Your users may never type `spoc`. The `init` and `app` commands mount into any
`argparse` parser, so you can publish them under your own console script:

```python
import argparse

from spoc.scaffold import cli as scaffold_cli

parser = argparse.ArgumentParser(prog="hello")
subcommands = parser.add_subparsers(dest="command", required=True)
scaffold_cli.register(subcommands)

print(sorted(subcommands.choices))
#> ['app', 'init']
```

Point your `[project.scripts]` entry at a `main()` that parses and dispatches to
`args.handler(args)`, and your users get `hello init` and `hello app`.

Two arguments shape what the mounted commands can reach:

- **`derive_kinds`** — a callable taking the project root and returning the kind
  names. Pass one and `app` derives kinds from the project's declaration;
  without it, users must pass `--kinds`.
- **`source_factory`** — decides which template sets resolve. Left out, only
  local sets resolve, so mounting the commands never silently acquires a network
  path. Pass a factory wired with a remote source to enable `gh:` and archive
  references.

`spoc.cli` is the worked example of exactly this: it is a composition root that
mounts each surface and injects both.

!!! warning "Tiering"

    `ENTRY_POINT_GROUP` and the `default` template set are **public** — the
    template path above is a promised contract. `scaffold.cli.register` is
    currently **internal**: it works, `spoc`'s own CLI is built on it, and it is
    not yet covered by the [stability policy](../api/stability.md). If you mount
    it, pin your SPOC version. Promoting it to a tiered mount point is an open
    question recorded in `DECISIONS.md`.

## Give your users types

`spoc stubs` writes a `.pyi` describing the project's resolution surface, so
`resolve("models:billing.invoice")` completes in an editor and type-checks. It
reads the registry, so it works for your kinds the same way it works for any
others — see [Get Editor Autocomplete](get-editor-autocomplete.md).
