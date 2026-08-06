# Registry API Reference

The flat component registry and the canonical identifier grammar.

Registrations are atomic and lose nothing under concurrency; after a
completed start, reads need no coordination.

## Registry Class

::: spoc.core.registry.Registry
    options:
      show_root_heading: true
      show_source: false

## Component Record

::: spoc.core.registry.Component
    options:
      show_root_heading: true
      show_source: false

## Identifier Grammar

`parse`, `compose`, and `Identifier` are part of the top-level surface —
import them as `spoc.parse`, `spoc.compose`, and `spoc.Identifier`; the
`spoc.core.identity` paths below are where they live, not how they are meant
to be reached. See the [public surface](public.md).

Validation and conversion are separate, and the split is by *origin*. A name the
author **states** is used verbatim and validated. A name the kernel **derives**
from an object is converted to snake_case by `to_snake_case` first, then validated
like any other value — so a PEP 8 class name yields the conventional segment
without the author restating it.

::: spoc.core.identity.parse
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.identity.compose
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.identity.validate_segment
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.identity.to_snake_case
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.identity.Identifier
    options:
      show_root_heading: true
      show_source: false

## Resolution Errors

Resolution fails per segment — kind, then namespace, then object name — each
error naming the failing segment, its value, and the valid candidates.

::: spoc.core.exceptions.MalformedIdentifierError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.InvalidSegmentError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.UnknownKindError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.UnknownNamespaceError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.UnknownObjectError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.DuplicateComponentError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.IdentityDivergenceError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.ComponentKindMismatchError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.MissingNameError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.UnmarkableObjectError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.MetadataContractError
    options:
      show_root_heading: true
      show_source: false
