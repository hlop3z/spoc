# SPOC — template reference resolution and retrieval

What **is**, as of remote template sources. A `--template` reference is parsed in
the pure core into the form it designates, then dispatched to exactly one
resolver. Retrieval sits entirely *before* the generation pipeline: by the time a
plan exists, a remote set is indistinguishable from a local one.

## Resolution is scheme-first and total

The reference's own spelling decides which kind of source is consulted, before
anything is looked up. Nothing falls through: a reference that designates one
kind never reaches another because the first came up empty.

```mermaid
flowchart TB
    ref["--template &lt;reference&gt;"]

    subgraph pure ["core — pure, no I/O"]
        parse["parse_reference<br/><i>total · stdlib only</i><br/>drive letter → scheme → separator"]
        refobj["<b>Reference</b><br/>kind · scheme · location<br/>revision · subdirectory"]
    end

    subgraph adapters ["sources — adapters"]
        direction LR
        builtin["built-in sets<br/><i>importlib.resources</i><br/>default · starter"]
        entry["entry points<br/><i>spoc.scaffold_templates</i>"]
        directory["local directory"]
        remote["<b>RemoteTemplateSource</b>"]
    end

    set["<b>TemplateSet</b><br/>+ reference · revision"]

    ref --> parse --> refobj
    refobj -->|"kind = NAME"| builtin
    refobj -->|"kind = NAME"| entry
    refobj -->|"kind = PATH"| directory
    refobj -->|"kind = REMOTE"| remote
    refobj -->|"no form matches"| refused["UnrecognizedReferenceError<br/><i>names the failing segment,<br/>lists recognized forms</i>"]

    builtin --> set
    entry --> set
    directory --> set
    remote --> set
```

`available()` lives on `EnumerableSource`, which only the built-in and
entry-point sources implement. A remote reference has no candidate set, so a
not-found error never invents one for it.

Two sets ship inside the distribution (`BUILTIN_SETS`): `default`, the minimal
bootable project, and `starter`, the default vocabulary wired end to end with a
transport-neutral projection module and a stdlib command surface. `starter` is
fully concrete — no `per_kind` repetition — because the `resources` kind's
lifecycle hooks cannot be expressed by name substitution.

## Retrieval, and where each control sits

Everything below happens before `build_plan`. A failure anywhere leaves the
destination untouched, because the destination has not been opened yet.

```mermaid
flowchart TB
    start["Reference (kind = REMOTE)"]

    resolve["<b>RevisionResolver</b><br/>moving ref → exact revision<br/><i>before anything is cached</i>"]
    cachehit{"<b>Cache</b><br/>revision retained?"}
    fetch["<b>Fetcher</b><br/>stdlib transport<br/>no scheme-downgrade redirect<br/><i>no response header names a path</i>"]

    subgraph admit ["archive — the trust boundary"]
        direction TB
        names["1 · name check<br/><i>absolute · traversal · drive</i>"]
        filter["2 · PEP 706 filter=data<br/><i>the adopted control</i>"]
        kind["3 · regular file or directory only"]
        contain["4 · resolve + is_relative_to<br/><i>after materialization</i><br/><b>neutralizes CVE-2025-4517</b>"]
        bounds["bounds · expanded size + member count<br/><i>halts mid-expansion</i>"]
    end

    retain["retained under the revision<br/><i>staged, then published</i>"]
    load["load_from_directory"]
    out["<b>TemplateSet</b><br/><i>identical to a local one<br/>from here on</i>"]

    start --> resolve --> cachehit
    cachehit -->|yes| load
    cachehit -->|no| fetch --> names --> filter --> kind --> contain --> bounds --> retain --> load --> out
```

### Why four layers and not one

Layers 1–3 can each be bypassed by a bug in the layer itself; layer 4 is the one
that holds regardless. That is not defensive habit — it is a response to what has
actually happened to this exact feature elsewhere:

| Advisory | Where it was | Layer that stops it here |
| --- | --- | --- |
| Django CVE-2021-3281 | absolute paths and `..` in `archive.extract()` | 1, 2 |
| Django CVE-2025-59682 | *partial* traversal via a shared common prefix | 4 — `is_relative_to` compares components, not string prefixes |
| Django, Aug 2026 | `Content-Disposition` filename reached `os.path.join` | Nothing the remote party says is used to build a path |
| CPython CVE-2025-4517 | traversal bypass **inside** `filter="data"` | 4 — the project's floor is 3.12, which admits unpatched interpreters |

The last row is why layer 4 exists at all. The tests for it stub layers 1 and 2
to pass everything, so they exercise containment rather than the standard
library's filter.

## How the plan is composed

A generation plan has two contributors, and only one of them is the template set.

```mermaid
flowchart TB
    set["<b>TemplateSet</b><br/><i>whoever authored it</i>"]
    values["values<br/>project_name · app_name<br/>kinds_args · kind_decorators · kind"]
    render["<b>build_plan</b><br/>substitute · reject escapes<br/><b>reject reserved destinations</b>"]
    rendered["rendered files"]

    origin["<b>Origin</b><br/><i>how the reference resolved</i>"]
    record["<b>record_file</b><br/>provenance.py<br/><i>json, not substitution</i>"]

    plan["<b>GenerationPlan</b>"]
    checks["is_empty · detect_conflicts"]
    commit["sink.commit<br/><i>all, or none</i>"]

    set --> render
    values --> render
    render --> rendered --> plan
    origin --> record --> plan
    plan --> checks --> commit
```

The record's values never enter `values`, so no substitution path reaches them —
a set cannot supply what the record says. `.spoc-template.json` is a reserved
destination, so a set cannot claim it either, and the refusal happens in the pure
core before anything is written. The record joins the plan *before* the checks,
so it inherits never-overwrite and all-or-nothing like any rendered file.

`spoc app` renders app-shaped files through the same `build_plan` but contributes
no record: it adds to a project that already has one, and never edits what the
author owns.

## Dependency direction

```mermaid
flowchart LR
    subgraph core ["core — pure"]
        plan["plan<br/>Reference · TemplateSet · GenerationPlan<br/><i>ports declared here</i>"]
        corefns["core<br/>parse_reference · build_plan · validation"]
        provenance["provenance<br/>Origin · record_file<br/><i>owns RECORD_NAME</i>"]
    end

    subgraph adapters ["adapters"]
        sources["sources"]
        remote["remote"]
        cache["cache"]
        archive["archive"]
        sink["sink"]
    end

    cliadapter["scaffold/cli<br/><i>parses argv, renders output</i>"]
    root["spoc/cli<br/><b>composition root</b><br/><i>the only place adapters are constructed</i>"]

    sources --> plan
    remote --> plan
    cache --> plan
    archive --> plan
    sink --> plan
    sources --> corefns
    provenance --> plan
    corefns --> provenance
    cliadapter --> plan
    root --> sources
    root --> remote
    root --> cache
    root --> cliadapter
```

The scaffold's own CLI never constructs a source. It receives a factory from the
composition root, so mounting that surface without wiring retrieval yields local
template sets only — a remote reference is the sole path by which the kernel
performs outbound network access, and it is visible in one place.
