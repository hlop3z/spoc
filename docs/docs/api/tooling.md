# Scaffold & Diagnostics API Reference

Every `spoc` subcommand is a thin adapter over one of these library calls —
`spoc.scaffold` generates ([`spoc init`](../cli.md#spoc-init) /
[`spoc app`](../cli.md#spoc-app)), `spoc.diagnostics` validates and reads
([`spoc check`](../cli.md#spoc-check) / [`spoc list`](../cli.md#spoc-list) /
[`spoc explain`](../cli.md#spoc-explain)). Code that never touches argv —
a downstream framework's own entry point, a build script — calls the same
operations. The kernel imports neither package; importing `spoc` loads
neither.

## Scaffold operations

The operations take their ports (template source, output sink) as arguments;
`spoc.scaffold` also exports the concrete adapters the CLI wires in —
`InstalledTemplateSources` and `DirectorySink`.

::: spoc.scaffold.operations.init_project
    options:
      show_root_heading: true
      show_source: false

::: spoc.scaffold.operations.add_app
    options:
      show_root_heading: true
      show_source: false

::: spoc.scaffold.operations.AddedApp
    options:
      show_root_heading: true
      show_source: false

## Diagnostic operations

Each operation is an isolated dry boot — no framework state, loaded app
modules, or import-path changes outlive a call.

::: spoc.diagnostics.core.check
    options:
      show_root_heading: true
      show_source: false

::: spoc.diagnostics.core.list_records
    options:
      show_root_heading: true
      show_source: false

::: spoc.diagnostics.core.explain
    options:
      show_root_heading: true
      show_source: false

## Diagnostic results

::: spoc.diagnostics.core.CheckReport
    options:
      show_root_heading: true
      show_source: false

::: spoc.diagnostics.core.Finding
    options:
      show_root_heading: true
      show_source: false

::: spoc.diagnostics.core.RecordInfo
    options:
      show_root_heading: true
      show_source: false
