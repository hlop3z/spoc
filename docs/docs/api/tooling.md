# API Reference — The Toolbox

The contained subpackages: data formats, the test harness, scaffolding, and
diagnostics. The kernel imports none of them; each is usable — or removable —
on its own.

## `spoc.formats`

::: spoc.formats
    options:
      show_root_heading: false
      members:
        - loads
        - dumps
        - read
        - write
        - collect
        - pointer
        - query
        - supported
        - FormatSupport
        - Collection

### Errors

::: spoc.formats.errors
    options:
      show_root_heading: false
      members:
        - FormatError
        - UnknownFormatError
        - MissingDependencyError
        - UnsupportedDirectionError
        - DecodeError
        - EncodeError
        - CollectionError
        - DuplicateEntryError
        - MalformedAddressError
        - PointerResolutionError

## `spoc.testing`

::: spoc.testing
    options:
      show_root_heading: false
      members:
        - ProjectTree
        - isolated
        - mode
        - import_state
        - MissingDependencyError

## `spoc.scaffold`

The library behind `spoc init` and `spoc app`, callable from your own code —
a downstream framework can ship its own templates and entry point.

::: spoc.scaffold
    options:
      show_root_heading: false
      members:
        - init_project
        - add_app
        - AddedApp
        - GenerationPlan
        - PlannedFile
        - TemplateSet
        - TemplateFile
        - TemplateSource
        - ProjectSink
        - DirectorySink
        - InstalledTemplateSources

## `spoc.diagnostics`

The library behind `spoc check`, `spoc list`, and `spoc explain`.

::: spoc.diagnostics.core
    options:
      show_root_heading: false
      members:
        - check
        - list_records
        - explain
        - CheckReport
        - Finding
        - RecordInfo
