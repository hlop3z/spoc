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
   it in `views.py` and SPOC refuses with a clear error. Where a block *lives*
   is what it *is*.
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

Within every app, `models.py` now loads before `views.py`. A dependency cycle
is refused at boot, with the cycle named.

An optional kind (`required=False`) may be missing from any app — every other
kind's module must exist, so a forgotten file is an error, not a silent gap.

## Talking across apps

Here's the part that keeps big projects clean: apps **don't import each
other**. They meet at the registry.

From the storefront example that ships with SPOC — the `orders` app uses the
`catalog` app's blocks without ever importing `apps.catalog`. This is the
example's real file, included at build time (the storefront's own test suite
runs it, and its `view` decorator is the storefront's naming — your
`framework.py` picks the names):

```python title="apps/orders/views.py" test="skip"
--8<-- "examples/apps/orders/views.py"
```

The only thing the two apps share is the name-tag grammar. Swap the catalog
app for another one that registers the same tags, and orders never notices.

Next: [start & stop — the lifecycle](lifecycle.md).
