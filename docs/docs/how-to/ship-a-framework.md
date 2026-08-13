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

Your users may never type `spoc`. Every command SPOC ships mounts into any
`argparse` parser, so you can publish them under your own console script:

```python
import argparse

from spoc.diagnostics import register as register_diagnostics
from spoc.projection import register as register_projection
from spoc.scaffold import register as register_scaffold
from spoc.stubs import register as register_stubs

parser = argparse.ArgumentParser(prog="hello")
subcommands = parser.add_subparsers(dest="command", required=True)

register_scaffold(subcommands)
register_diagnostics(subcommands)
register_stubs(subcommands)
register_projection(subcommands)

print(sorted(subcommands.choices))
#> ['app', 'check', 'explain', 'init', 'list', 'projection', 'stubs']
```

Point your `[project.scripts]` entry at a `main()` that parses and dispatches to
`args.handler(args)`, and your users get the whole line under your own name:
`hello init` and `hello app` to generate, `hello check` to validate before
runtime, `hello list` and `hello explain` to read the registry, `hello stubs`
for editor autocomplete, and `hello projection` to hand the registry to another
tool as JSON.

Mount only what you want. Each `register` is independent and additive, so a
framework that would rather own its own `check` can mount the other three and
leave that one out.

Mounting describes commands on your parser and does nothing else — it reads no
arguments, writes no output, and never ends the process. Parsing, dispatch, and
the exit code stay yours, which is what lets you rename, wrap, or refuse
anything you mounted.

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

!!! info "Tiering"

    `ENTRY_POINT_GROUP` and the `default` template set are **public**, so the
    template path above is a promised contract. All four `register` functions are
    **provisional** under the [stability policy](../api/stability.md): documented
    and intended for exactly this use, breakable in a minor release but never in
    a patch. Pin a minor line, not an exact version.

    What is promised is which commands each mount contributes and what invoking
    them does. What is *not* promised is the type of `subcommands` — that belongs
    to `argparse`, and guaranteeing it would commit your framework to `argparse`
    as firmly as it commits SPOC. The tier settles once a framework outside SPOC
    has actually mounted these, which fixes the shape against a real second
    caller, or once SPOC commits to a parser choice and the mount can take a type
    it owns.

## Shut down where your surface has already drained

SPOC serializes its own lifecycle transitions, but it does not wait for readers.
While `start` or `shutdown` is in flight, a `resolve` from outside that transition
is refused with `FrameworkTransitioningError` rather than served a half-built or
already-emptied registry.

That error should be unreachable in a served application, because your surface
already knows when its work is finished — it admitted the work. Call shutdown at
the point where it has:

| Surface | Call `shutdown()` / `ashutdown()` | Why it's safe there |
| --- | --- | --- |
| ASGI — Starlette, FastAPI, Falcon | In the lifespan shutdown handler (after the `yield` in a `lifespan` context manager) | The ASGI spec sends `lifespan.shutdown` only once the server "has stopped accepting connections and closed all active connections" |
| gRPC | After `await server.stop(grace)` returns | New RPCs are already rejected with `UNAVAILABLE`, and in-flight ones had the grace period to finish |
| WSGI behind a worker manager | In the worker's exit hook, after the worker stops accepting | The manager stops routing before it signals the worker |

Some surfaces have no ambient drain, and there the ordering is yours to write:

- a message-queue loop (ZeroMQ, raw sockets) — stop receiving, finish the message
  in hand, *then* shut down;
- a task your app spawned itself with `asyncio.create_task` — an ASGI server drains
  connections, not tasks you started behind its back. Cancel and await it first;
- worker threads, schedulers, and CLIs that outlive a request.

Whatever you resolve stays yours after the transition ends. SPOC returns the object
and never sees what you do with it, so a component resolved before shutdown and used
after it is not something the kernel can refuse on your behalf.

## Give your users types

`spoc stubs` writes a `.pyi` describing the project's resolution surface, so
`resolve("models:billing.invoice")` completes in an editor and type-checks. It
reads the registry, so it works for your kinds the same way it works for any
others — see [Get Editor Autocomplete](get-editor-autocomplete.md).
