# The Public Surface

Everything a framework author needs is importable from `spoc` directly — the
package's `__all__` is the contract. The `spoc.core.*` paths that appear on
the reference pages are where the objects live; they are reachable for anyone
extending the kernel, but they are not how the surface is meant to be
imported.

```python
import spoc

framework = spoc.Framework("models", spoc.KindSpec("views", depends_on=("models",)))
ident = spoc.parse("models:blog.post")
```

## Declaration

| Symbol | Documented on |
| --- | --- |
| `spoc.Framework` | [Framework API](framework.md) |
| `spoc.KindSpec` | [Declaration API](components.md) |
| `spoc.Config` | [Framework API](framework.md) |

## Registry

| Symbol | Documented on |
| --- | --- |
| `spoc.Registry` | [Registry API](registry.md) |
| `spoc.Component` | [Registry API](registry.md) |

## Identity

| Symbol | Documented on |
| --- | --- |
| `spoc.Identifier` | [Registry API](registry.md#identifier-grammar) |
| `spoc.parse` | [Registry API](registry.md#identifier-grammar) |
| `spoc.compose` | [Registry API](registry.md#identifier-grammar) |

## Exceptions

All sixteen errors are direct subclasses of `spoc.SpocError`, so one
`except spoc.SpocError` catches everything the kernel raises. Identifier and
registry errors are documented on the
[Registry API](registry.md#resolution-errors) page; the rest on
[Core Utilities](core-utils.md).

```text
AppNotFoundError            MissingModuleError
CircularDependencyError     ConfigurationError
MalformedIdentifierError    InvalidSegmentError
UnknownKindError            UnknownNamespaceError
UnknownObjectError          UnresolvedReferenceError
DuplicateComponentError     IdentityDivergenceError
ComponentKindMismatchError  MissingNameError
UnmarkableObjectError       MetadataContractError
```

## Package

`spoc.__version__` — the installed version string.

## Opt-in subpackages

Not part of `spoc.__all__` — imported explicitly when wanted, and the kernel
never imports them:

- **`spoc.formats`** — reading, writing, and querying data files
  ([Data & Formats](../advanced/data-formats.md))
- **`spoc.testing`** — isolation scopes for tests
  ([Testing Your App](../advanced/testing.md))
- **`spoc.scaffold`** and **`spoc.diagnostics`** — the library form of the
  CLI's operations ([Scaffold & Diagnostics](tooling.md))
