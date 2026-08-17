# Apps & Modes

An **app** is a folder of related blocks — one file per kind. If your
framework declares `models` and `views`, an app looks like this:

```
apps/blog/
├── __init__.py
├── models.py     # blocks of kind "models"
└── views.py      # blocks of kind "views"
```

Three simple rules:

1. **The folder name is the namespace.** Blocks in `apps/blog/` get tags like
   `models:blog.post`.
2. **The file name is the kind.** A `models` block lives in `models.py` — put
   it in `views.py` and SPOC refuses with a clear error. Where a block _lives_
   is what it _is_.
3. **Importing is fine.** `from .models import Post` inside `views.py` is just
   a use, not a second claim. SPOC knows the difference.

`spoc app <name>` generates this shape for you, with the kinds read from your
own `framework.py`.

## Installing apps

An app exists when its folder is on disk; it's **installed** when a mode lists
it in `spoc.toml`:

```toml
[spoc.apps]
production = ["apps.core"]
development = ["apps.blog"]     # only boots during development
```

Each entry is a normal dotted Python path, imported exactly as written — the
last segment becomes the namespace. Modes cascade (development ⊃ staging ⊃
production), as covered in [The Settings File](../getting-started/configuration.md).

## Load order: `depends_on`

If views need models to exist first, say so once, in the declaration:

```python
import spoc

framework = spoc.Framework(
    "models",
    spoc.KindSpec("views", depends_on=("models",)),
)
```

A kind is a **phase**, and a phase spans every app. _All_ apps' `models.py` load
and initialize before _any_ app's `views.py` — not just within one app. So a
`views` hook that reads the registry sees every model in the project, never a
half-built world. A dependency cycle is refused at boot, with the cycle named.

An optional kind (`required=False`) may be missing from any app — every other
kind's module must exist, so a forgotten file is an error, not a silent gap. An
app that omits one moves nothing: its remaining modules stay in their own
phases, exactly where they would be if it had the file.

## Ordering two apps: the `[spoc.apps]` list

Inside one phase, apps go in the order they are listed. That is the whole knob,
and it is worth knowing about for exactly one reason — hooks fire in load order:

```toml
[spoc.apps]
development = ["apps.core", "apps.blog"]   # core's hooks fire first
```

Both apps' `models` hooks run before either app's `views` hook (that is the
phase rule above), and within the `models` phase `apps.core` runs before
`apps.blog`. Reorder the list and you reorder the hooks. Shutdown runs the
whole thing backwards.

There is deliberately no way to say "all of `apps.core` before any of
`apps.blog`" — that would put one app's `views` ahead of another's `models` and
break the phase guarantee everything else here rests on.

## Talking across apps

Here's the part that keeps big projects clean: apps **don't import each
other**. They meet at the registry.

From the storefront example that ships with SPOC — the `orders` app uses the
`catalog` app's blocks without ever importing `apps.catalog`. This is the
example's real file, included at build time, so the storefront's own test suite
runs exactly what you read here:

```python {title="apps/orders/views.py" test="skip"}
--8<-- "examples/apps/orders/views.py"
```

The only thing the two apps share is the name-tag grammar. Swap the catalog
app for another one that registers the same tags, and orders never notices.

Next: [start & stop — the lifecycle](lifecycle.md).
