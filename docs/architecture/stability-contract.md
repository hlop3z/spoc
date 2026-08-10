# SPOC — the stability contract

What **is**, as of the derived stability contract. The tier of every importable
element is a consequence of how the source exposes and documents it — there is no
list of names to keep in step, because there is no list.

This mirrors the kernel's own shape — one source, many projections — applied to the
package's surface rather than to a project's components.

## Source of truth, and what derives from it

**The source code is the authority.** Two facts decide an importable element's tier,
and both are read off the artifact itself: whether a package re-exports the name, and
whether its own documentation carries the provisional notice.

`[tool.spoc.stability]` in `pyproject.toml` still exists, but only for the kinds no
static observer can attribute a tier to — the command, the entry point, the fixtures,
the extras, the config schema, the template set. An importable name there is refused.

```mermaid
flowchart TB
    subgraph authority ["The artifact — where every importable tier is decided"]
        direction LR
        exports["<b>__all__</b><br/>package re-export<br/><i>exposed ⇒ public</i>"]
        notice["<b>Provisional notice</b><br/>in the element's own docstring<br/><i>+ what would settle it</i>"]
    end

    manifest["[tool.spoc.stability]<br/>pyproject.toml<br/><i>non-importable kinds only —<br/>a dotted path here is refused</i>"]

    rules["<b>derive_tier</b><br/>public · provisional · internal<br/><i>total over its inputs</i>"]

    subgraph projections ["Projections — derived, never authored twice"]
        direction LR
        docs["docs/api/stability.md<br/>the tiers, in prose"]
        gate["apicheck<br/>the enforcing gate"]
        delta["apidiff<br/>the cross-release gate"]
    end

    exports --> rules
    notice --> rules
    rules --> gate
    manifest --> gate
    rules --> docs
    rules --> delta
    gate -. "fails the build when the<br/>source and the rules disagree" .-> rules

    classDef source fill:#1f2937,stroke:#60a5fa,stroke-width:2px,color:#f9fafb
    classDef proj fill:#111827,stroke:#4b5563,color:#e5e7eb
    class exports,notice,rules source
    class docs,gate,delta,manifest proj
```

## What may be exposed at all

The rules above say what tier follows *from* exposure. A separate rule governs the
exposure itself, so a published namespace cannot grow without anything being broken:
a name is re-exported only if a consumer outside the package must write it to invoke
an operation, implement a contract the package accepts, distinguish a condition they
can respond to differently, or supply a value the package reads. Anything that exists
so the package can assemble itself stays in its defining module.

## How the check is wired

The core is pure: it is handed a declared contract and an observed surface and
returns findings. Every adapter around it reaches out to exactly one place, so
replacing any of them touches one file. The tool lives in `scripts/py/`, outside
the distribution — a checker shipped inside `spoc` would need a tier of its own and
would have to police itself.

```mermaid
flowchart LR
    subgraph inputs ["Adapters — the only code that reaches out"]
        direction TB
        mf["manifest.py<br/><i>tomllib</i><br/>non-importable kinds"]
        ex["extract.py<br/><i>griffe, static</i><br/>exposure + notice,<br/>per importable name"]
        pk["packaging.py<br/><i>pyproject + AST</i><br/>scripts, entry points,<br/>extras, fixtures, template sets"]
    end

    core["<b>core.py</b> — pure<br/>declared vs observed<br/>no I/O, no introspection"]

    subgraph out ["Findings"]
        direction TB
        fatal["undeclared · absent<br/>unresolved-tier · unsettled-tier<br/><b>exit 1</b>"]
        soft["unverifiable<br/><i>reported, never silent</i><br/>exit 0"]
    end

    mf --> core
    ex --> core
    pk --> core
    core --> fatal
    core --> soft

    cli["cli.py — argument parsing<br/>and exit code only"] -.->|drives| core

    classDef pure fill:#1f2937,stroke:#34d399,stroke-width:2px,color:#f9fafb
    classDef adapter fill:#111827,stroke:#60a5fa,color:#e5e7eb
    classDef result fill:#111827,stroke:#4b5563,color:#e5e7eb
    class core pure
    class mf,ex,pk,cli adapter
    class fatal,soft result
```

Dependencies point inward. `core.py` imports no adapter, knows nothing of TOML,
griffe, or the terminal, and is the only module with tests of its own — it is where
every decision is made.

## Why `unverifiable` is a finding rather than a pass

Griffe documents that it cannot see console scripts, entry points, or extras;
`packaging.py` covers those, and some kinds — a file *schema*, for instance — no
observer covers at all. Rather than let a declared element pass because nothing
looked at it, the core compares each element's kind against the set of kinds the
observers claim, and reports the remainder.

It does not fail the build, because a coverage gap is not a divergence. It is always
printed, because a check that silently skips what it cannot inspect reads as
"everything passed" when it isn't.
