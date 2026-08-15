# SPOC — documentation integrity

What **is**, as of the docs-dx change. The documentation cannot drift from the
code because nothing load-bearing in it is authored twice: snippets execute,
reference listings derive, and the two hand-written indexes are held complete
by tests. One source, many projections — the kernel's own shape, applied to
the docs.

## The three snippet states

Every Python fence under `docs/docs/` is in exactly one state; an unmarked
fence that doesn't run fails the suite, so silence is not a state.

```mermaid
flowchart TB
    fences["Python fences in docs/docs/**/*.md"]

    fences -->|"no title="| standalone["<b>Standalone</b><br/>runs as its own module<br/><i>prints must match #&gt; comments</i>"]
    fences -->|"title=&quot;path&quot;"| tree["<b>Project file</b><br/>written verbatim into a per-page tree,<br/>in page order — later same title overwrites"]
    fences -->|"test=&quot;skip&quot;"| skipped["<b>Marked</b><br/>display-only; counted against<br/>an explicit ceiling"]

    tree --> entry["title=&quot;main.py&quot; runs as a subprocess<br/><i>exactly what a reader would type</i>"]
    entry --> tutorial["Build a Framework page:<br/>own runner — boots the page's server on an<br/>ephemeral port and asserts the curl payloads"]

    standalone & entry & tutorial --> suite["tests/test_docs_examples.py<br/><i>the Unit tests gate row</i>"]
```

## Derived reference, checked indexes

```mermaid
flowchart LR
    subgraph sources ["Source of truth"]
        all_list["__all__<br/>per module"]
        parser["spoc.cli — the argparse surface"]
        starter["the starter template set"]
        examples["examples/ — the storefront"]
    end

    subgraph build ["Docs build (strict — a warning fails the gate)"]
        apiref["api/public.md · api/tooling.md<br/><i>mkdocstrings renders the exports</i>"]
        clipage["tools/cli.md<br/><i>cli_help() macro captures --help</i>"]
        include["learn/apps.md<br/><i>pymdownx.snippets includes the real file</i>"]
    end

    subgraph tests ["Test-held (authored prose, mechanical completeness)"]
        errors["api/errors.md — every exported<br/>exception has a row"]
        payoff["index.md / starter.md — the displayed<br/>--help diffs against a real generation"]
    end

    all_list --> apiref
    all_list --> errors
    parser --> clipage
    examples --> include
    starter --> payoff
```

The split matters: the **build** column regenerates content, so it can never
be stale; the **tests** column keeps hand-written prose but makes
_incompleteness_ a failure. Both run in the gate (`.canon/checks.md` — the
Docs build and Unit tests rows).
