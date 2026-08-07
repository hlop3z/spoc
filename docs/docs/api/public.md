# API Reference — The Kernel

Everything on this page is importable from `spoc` directly. This is the whole
public surface of the kernel — if it isn't here, a framework author doesn't
need it.

## Framework

::: spoc.Framework

::: spoc.Config

## Declaration

::: spoc.KindSpec

## Registry

::: spoc.Registry

::: spoc.Component

## Identity

::: spoc.Identifier

::: spoc.parse

::: spoc.compose

## Exceptions

Every error SPOC raises is a subclass of `SpocError`, so one `except` catches
them all — and each one names precisely what failed.

::: spoc.core.exceptions
    options:
      show_root_heading: false
      members:
        - SpocError
        - ConfigurationError
        - AppNotFoundError
        - MissingModuleError
        - CircularDependencyError
        - MalformedIdentifierError
        - InvalidSegmentError
        - UnknownKindError
        - UnknownNamespaceError
        - UnknownObjectError
        - UnresolvedReferenceError
        - DuplicateComponentError
        - IdentityDivergenceError
        - ComponentKindMismatchError
        - MissingNameError
        - UnmarkableObjectError
        - MetadataContractError
