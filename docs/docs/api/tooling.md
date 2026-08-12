# API Reference — The Toolbox

The contained subpackages: data formats, the test harness, scaffolding,
diagnostics, and the registry projection. The kernel imports none of them; each
is usable — or removable — on its own.

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

The library behind `spoc check`, `spoc list`, and `spoc explain`. Records are
described by `spoc.projection.ComponentEntry` below — one registry has one
description, and these commands render it after a full boot.

::: spoc.diagnostics.core
    options:
      show_root_heading: false

## `spoc.projection`

The library behind `spoc projection`, and the one description of a registered
component that every other describing surface reads.

`project()` runs a collect-only boot — discovery without initialization — so a
project whose startup hooks would fail is still describable. `dumps()` renders
the document; `schema_path()` locates the published JSON Schema it validates
against. The document shape, not this dataclass, is the contract: see
[the CLI page](../tools/cli.md#spoc-projection-hand-your-registry-to-another-tool)
for the format itself.

::: spoc.projection
    options:
      show_root_heading: false
