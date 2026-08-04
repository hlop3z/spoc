# Declaration API Reference

The declaration layer: what a kind is, and how objects are marked as components
of one. Markers are attached by the decorator `framework.kind()` hands out (or by
the low-level `component` function), and discovery turns them into registry
records at start.

## KindSpec

Everything the kernel knows about one declared kind lives on this record —
its dependencies, whether apps must provide it, the metadata contract its
components carry, and its lifecycle hooks. There is no parallel structure keyed
by kind name that could disagree with it.

A bare string is accepted wherever a `KindSpec` is, as shorthand for one with all
defaults: `Framework("models")` and `Framework(KindSpec("models"))` are the same
declaration.

::: spoc.core.declaration.KindSpec
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.declaration.as_kind_spec
    options:
      show_root_heading: true
      show_source: false

## Registration Handles

::: spoc.core.declaration.registrar
    options:
      show_root_heading: true
      show_source: false

## Component Decorator

::: spoc.core.declaration.component
    options:
      show_root_heading: true
      show_source: false

## Declaration Marker

::: spoc.core.declaration.Internal
    options:
      show_root_heading: true
      show_source: false

## Metadata Contract

A kind that states a `metadata` type has every component's metadata checked
against it at registration. A kind that states none accepts no metadata at all —
there is no untyped channel by default.

::: spoc.core.declaration.check_metadata
    options:
      show_root_heading: true
      show_source: false

## Helper Functions

::: spoc.core.declaration.is_spoc
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.declaration.get_info
    options:
      show_root_heading: true
      show_source: false
