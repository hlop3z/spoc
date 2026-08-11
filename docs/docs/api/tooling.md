# API Reference — The Toolbox

The contained subpackages: data formats, the test harness, scaffolding, and
diagnostics. The kernel imports none of them; each is usable — or removable —
on its own.

Each listing is derived from the module's own `__all__` at build time — a new
export appears here on the next build, with no edit to this page.

## `spoc.formats`

The format errors are part of the same surface and render here alongside the
functions — `FormatError` is the one to catch.

::: spoc.formats
    options:
      show_root_heading: false

## `spoc.testing`

::: spoc.testing
    options:
      show_root_heading: false

## `spoc.scaffold`

The library behind `spoc init` and `spoc app`, callable from your own code —
a downstream framework can ship its own templates and entry point.

The operations take their ports as arguments, so generation is callable without
argv and testable without a filesystem or a network. `InstalledTemplateSources`
resolves a reference by its form; pass it a `RemoteTemplateSource` to enable
retrieval, or leave it out and only local sets resolve.

::: spoc.scaffold
    options:
      show_root_heading: false

## `spoc.diagnostics`

The library behind `spoc check`, `spoc list`, and `spoc explain`.

::: spoc.diagnostics.core
    options:
      show_root_heading: false
