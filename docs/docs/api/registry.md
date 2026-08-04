# Registry API Reference

The flat component registry and the canonical identifier grammar.

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

::: spoc.core.identifier.parse
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.identifier.compose
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.identifier.validate_segment
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.identifier.Identifier
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

::: spoc.core.exceptions.ComponentKindMismatchError
    options:
      show_root_heading: true
      show_source: false

::: spoc.core.exceptions.MissingNameError
    options:
      show_root_heading: true
      show_source: false
