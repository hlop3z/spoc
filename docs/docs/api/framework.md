# Framework API Reference

This page provides detailed API documentation for the Framework module in SPOC.
Both classes are top-level exports — import them as `spoc.Framework` and
`spoc.Config` (see the [public surface](public.md)).

The framework object is the single declaration point and the composition root. It
owns the registry, the loader, and the configuration adapter, and it is the only
place they are wired together.

Per-kind attributes — dependency order, optionality, the metadata contract, and
lifecycle hooks — are declared on
[`KindSpec`](components.md#spoc.core.declaration.KindSpec), not on the framework.
There is no decorator form for them: a kind attribute is stated on the kind it
describes, or nowhere.

## Framework Class

::: spoc.framework.Framework
    options:
      show_root_heading: true
      show_source: false

## Config Class

::: spoc.framework.Config
    options:
      show_root_heading: true
      show_source: false
