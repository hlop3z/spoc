# API Reference — The Kernel

Everything on this page is importable from `spoc` directly. This is the whole
public surface of the kernel — if it isn't here, a framework author doesn't
need it.

The listing below is derived from the package's own `__all__` at build time —
a new export appears here on the next build, with no edit to this page.

## The shape of the surface

It is a short list, and most of it is error types. What you actually *build*
with is eleven names in four groups:

| Group | Names | What it is for |
| --- | --- | --- |
| **Declaration** | `Framework`, `KindSpec`, `KindHandle`, `component`, `Config` | Saying which kinds exist, and marking objects as belonging to one. `Framework` is the object your whole framework is; `KindSpec` declares one kind in full (dependencies, hooks, metadata contract) where a bare string won't do; `KindHandle` is the ready-made decorator `framework.kind()` returns; `component` marks an object without one; `Config` is your settings after a boot, on `framework.config`. |
| **The registry** | `Registry`, `Component` | What a boot produces. `Registry` is the shelf, enumerable and narrowable by facet; `Component` is one record on it — the identifier, its three segments, and the object itself. Every surface you build is a loop over these. |
| **Identity** | `Identifier`, `parse`, `compose` | The name grammar as values. `Identifier` is a parsed `kind:namespace.object_name`; `parse` and `compose` convert between it and the string. Reach for these when you are *manipulating* names rather than resolving them. |
| **The package** | `__version__` | What you are running. |

Everything else on this page is an **error type**. That ratio is intentional:
the kernel does a small number of things and refuses precisely, so most of the
surface exists to tell you what went wrong. You do not need to learn them —
every one subclasses `SpocError`, so a single `except spoc.SpocError` catches
the lot, and each names exactly what failed in its message and on its
attributes. Match on the type, never the message text.

For the trigger-and-fix table, see the [error index](errors.md); for which of
these names carry which promise, see
[Stability & Versioning](stability.md).

## Everything, in full

::: spoc
    options:
      show_root_heading: false
