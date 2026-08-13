# SPOC — system architecture

What **is**, as of the kernel collapse. SPOC is a component registry with a
dependency-ordered lifecycle: one `Framework` object declares the kind set, apps
declare components inward, surfaces project outward from the registry, and every
dependency points at the kernel — never out of it.

Throughout this document **kernel** means the core package (`spoc` proper, the
box below) as opposed to the contained subpackages — `spoc.formats`,
`spoc.testing`, `spoc.diagnostics`, `spoc.scaffold`, `spoc.stubs`,
`spoc.projection`. It is a boundary within the distribution, not a claim that
SPOC schedules, isolates, or mediates anything.

## The shape

Four jobs, and the module boundaries match them. The core is pure — it performs
no I/O and imports nothing outside the kernel. The adapters touch the outside
world: one imports modules, one reads files. `Framework` is the only place they
meet.

The registry is **not** owned by the loader. That inversion — a pure core concern
nested inside an adapter — is what forced the loader to know what a kind is, and
removing it is the point of this shape.

```mermaid
flowchart TB
    subgraph surfaces ["Surfaces — thin adapters (not part of SPOC)"]
        direction LR
        fastapi["FastAPI / Robyn<br/>HTTP"]
        cli["CLI"]
        workers["Workers / events<br/>(e.g. an execution engine app)"]
    end

    root["<b>Framework</b><br/><i>composition root — the only wiring</i><br/>KindSpec × N · kind() handles · on_ready"]

    subgraph kernel ["SPOC kernel — zero runtime dependencies"]
        direction TB

        subgraph core ["core — pure, no I/O"]
            direction TB
            identity["identity<br/>grammar · parse · compose<br/>snake_case derivation"]
            declaration["declaration<br/>KindSpec · markers · discovery"]
            registry[("Registry<br/>flat store of Component records<br/>kind : namespace . object_name")]
        end

        subgraph adapters ["adapters — touch the outside world"]
            direction LR
            loader["loader<br/>import · dep order · lifecycle (sync + async)<br/><i>kind-blind</i>"]
            config["config<br/>spoc.toml only · declarable mode cascade"]
        end
    end

    subgraph apps ["Apps — the domain, declared by dotted path (apps.blog)"]
        direction LR
        blog["blog/<br/>models.py · views.py"]
        shop["shop/<br/>models.py · views.py"]
    end

    declaration --> identity
    registry --> identity
    loader --> core
    config --> core
    root --> core
    root --> adapters
    registry -. "on_ready(registry)" .-> root

    surfaces -- "enumerate · resolve<br/>(read-only, public API)" --> registry
    apps -- "declare<br/>@model = framework.kind('models')" --> declaration
```

## A kind is one record

Every per-kind attribute rides one `KindSpec`, so no second structure keyed by
kind name can disagree with it. A bare string is shorthand for a spec with all
defaults.

```mermaid
flowchart LR
    spec["<b>KindSpec</b>"]
    spec --- n["name<br/><i>module file name + identifier segment</i>"]
    spec --- d["depends_on<br/><i>inter-kind load order</i>"]
    spec --- r["required<br/><i>may an app omit this module?</i>"]
    spec --- m["metadata<br/><i>the type its components carry</i>"]
    spec --- h["on_startup / on_shutdown<br/><i>lifecycle hooks</i>"]
```

## Absent is not broken

Optionality is decided per kind, never framework-wide, and it only governs
*absence*. A module that exists and raises while importing is always an error —
the author wrote something that does not work rather than declining to write it.
The two are told apart by which module the import system reports as missing.

```mermaid
flowchart LR
    reg["register(app.kind)"] --> imp{"imports?"}
    imp -- yes --> ok["loaded"]
    imp -- "ModuleNotFoundError<br/>naming a *different* module" --> broken["raise — present but broken"]
    imp -- "ModuleNotFoundError<br/>naming *this* module" --> q{"kind.required?"}
    q -- yes --> miss["MissingModuleError<br/>+ app, kind, expected module"]
    q -- no --> skip["skipped, contributes nothing"]
```

## The identifier

```mermaid
flowchart LR
    id["models : blog . post"]
    kind["kind<br/>= module file name<br/>(closed set, declared on Framework)"]
    ns["namespace<br/>= final segment of the app path"]
    name["object_name<br/>= declared name"]

    id --- kind
    id --- ns
    id --- name
```

Every segment matches `^[a-z][a-z0-9_]*$`, validated at registration. A name
derived from an object's own name is converted to snake_case first
(`UserAccount` → `user_account`); a name stated explicitly is verbatim, and
lookup never converts. Exactly three segments; no operation suffix.

## Resolution

```mermaid
flowchart LR
    input["resolve(identifier)"] --> parse{"parses?"}
    parse -- no --> e0["MalformedIdentifierError"]
    parse -- yes --> k{"kind<br/>declared?"}
    k -- no --> e1["UnknownKindError<br/>+ declared kinds"]
    k -- yes --> n{"namespace has<br/>that kind?"}
    n -- no --> e2["UnknownNamespaceError<br/>+ candidate namespaces"]
    n -- yes --> o{"object_name<br/>registered?"}
    o -- no --> e3["UnknownObjectError<br/>+ candidate names"]
    o -- yes --> rec["Component record<br/>(object returned unexecuted)"]
```

## The scaffolder

`spoc init` is a surface, not kernel. It runs **before** a project exists, so
it appears nowhere in the flow above: nothing in the kernel imports it, and
removing it changes nothing at runtime. Like every other surface it is a thin
adapter over a pure core, and its dependencies point inward.

```mermaid
flowchart LR
    cli["spoc init<br/><i>argparse entry point</i><br/>parses · renders · no logic"]

    subgraph core ["Scaffold core — pure, no I/O"]
        direction TB
        validate["validate names<br/><i>kernel's identity grammar</i>"]
        plan["build plan<br/><i>$name substitution only</i>"]
        conflicts["detect conflicts<br/><i>plan vs listing</i>"]
        validate --> plan --> conflicts
    end

    subgraph adapters ["Adapters"]
        direction TB
        source["TemplateSource<br/>built-in set · entry points"]
        sink["ProjectSink<br/>stage → verify → commit"]
    end

    templates[("Template sets<br/><i>directories of native-format files</i><br/>+ manifest declaring values")]
    project["Generated project<br/>config · framework.py · one app · main.py"]

    cli --> core
    source -- "loads" --> core
    templates --> source
    core -- "GenerationPlan<br/>(all-or-nothing)" --> sink
    sink --> project
    project -. "starts unedited<br/><i>asserted by the test suite</i>" .-> templates
```

The dotted edge is the mechanism that keeps templates honest: the suite
generates a project, starts it, and asserts the registry, so a kernel change
that would break new projects fails here rather than reaching users.

## The data surface

`spoc.formats` is a **contained subpackage** of the `spoc` distribution. The kernel never
imports it and importing `spoc` never loads it — there is no edge between them in either
direction, a boundary the test suite enforces rather than packaging. It exists for the
*project's* own data — fixtures, tables, per-app settings — never for the kernel's
configuration, which stays `spoc.toml` through stdlib `tomllib`. The collection-key grammar
restates the kernel's segment convention locally: the two surfaces share a convention,
never code.

```mermaid
flowchart TB
    project["Project code<br/><i>calls it directly — not a lifecycle hook</i>"]

    subgraph formats ["spoc.formats — contained subpackage, imports resolve lazily"]
        direction TB

        subgraph fcore ["core — pure, no I/O, stdlib only"]
            direction TB
            port["Codec port<br/><i>one lazy factory per direction</i>"]
            freg["FormatRegistry<br/>by name · by extension"]
            ops["operations<br/>loads · dumps · read · write · collect"]
        end

        subgraph fad ["adapters — one per format"]
            direction LR
            std["json · csv · toml-read<br/><i>standard library</i>"]
            opt["yaml · xml · toml-write<br/><i>behind extras</i>"]
        end

        access["access<br/>RFC 6901 pointer · RFC 9535 query"]
    end

    ir[("JSON representation<br/><i>object · array · string<br/>number · boolean · null</i>")]
    files[("Files on disk<br/>a tree of mixed formats")]

    project --> ops
    project --> access
    ops --> freg --> port
    port -.-> std
    port -.-> opt
    files --> ops
    ops --> ir
    access --> ir
```

The dotted edges are the laziness: a codec's dependency is imported the first time that
*direction* of that *format* is used, so importing `spoc.formats` on a bare install pulls in
nothing, and a missing extra fails naming itself rather than as an `ImportError`.

Reading and querying are separate boxes on purpose. Addressing is split by failure semantics —
a pointer names one value or raises, a query returns a possibly-empty list — and the two are
never relaxed into each other.

## The test harness

`spoc.testing` is the third contained subpackage, under the same boundary as the other
two: the kernel never imports it, importing `spoc` never loads it, and the suite pins
both directions. It consumes only the kernel's *public* contracts — construction,
`start`/`shutdown`, resolution — and owns the process state a boot touches in a test
(`sys.path`, `sys.modules`), which the kernel itself never mutates.

```mermaid
flowchart TB
    suite["A project's test suite<br/><i>any runner, or none</i>"]
    pytest["pytest<br/><i>the only importer of plugin</i>"]

    subgraph testing ["spoc.testing — contained subpackage"]
        direction TB
        plugin["plugin<br/><i>fixtures: spoc_tree · spoc_isolated · spoc_framework</i>"]
        core["core<br/>isolated · import_state · mode"]
        tree["tree<br/>ProjectTree → bootable directory"]
    end

    kernel["Kernel public API<br/>Framework · start · shutdown · resolve"]

    suite --> core
    suite --> tree
    pytest -.->|pytest11 entry point| plugin
    plugin --> core
    plugin --> tree
    core --> kernel
    tree -.->|toml extra, lazy| emit["TOML emission"]
```

The dotted edge to `plugin` is the inertness contract: the entry point is metadata, so
pytest is the only thing that ever imports the module and a runtime install never loads
a test runner. The dotted edge to TOML emission mirrors the formats rule — a missing
extra fails naming itself.

## The diagnostics and the composed CLI

`spoc.diagnostics` is the fourth contained subpackage: pre-runtime validation
(`check`) and registry introspection (`list`, `explain`) as library-first
operations. A diagnostic run is an isolated dry boot — it composes
`spoc.testing`'s scopes (the one sanctioned edge between contained
subpackages) and the kernel's public API, so nothing a run imports or
registers outlives it. The `spoc` console script is one composed parser in
`spoc.cli`; each surface registers its own subcommands and stays a thin
adapter.

```mermaid
flowchart TB
    console["spoc console script"] --> cli["spoc.cli — composed parser<br/><i>parse · dispatch · map refusals to exit codes</i>"]
    cli -->|init| scaffold["spoc.scaffold"]
    cli -->|check · list · explain| diag
    cli -->|stubs| stubs
    cli -->|projection| proj

    subgraph diag ["spoc.diagnostics — contained subpackage"]
        direction TB
        dcli["cli — subcommand adapters"]
        dcore["core<br/>check · list_records · explain"]
        dcli --> dcore
    end

    subgraph stubs ["spoc.stubs — contained subpackage"]
        direction TB
        scli["cli — subcommand adapter"]
        sman["manifest — describe(): projection + type refs"]
        sext["extract — live objects → type references"]
        semit["emit — manifest → stub text (pure)"]
        scli --> sman --> sext
        sman --> semit
    end

    subgraph proj ["spoc.projection — the one description of a registry"]
        direction TB
        pcli["cli — subcommand adapter"]
        pprod["produce — collected(): collect-only boot"]
        pdoc["document — records → JSON (pure)"]
        pschema[["schema.json — published JSON Schema"]]
        pcli --> pprod --> pdoc
        pdoc -.validates against.-> pschema
    end

    locate["spoc.locate<br/>framework:framework convention · mod:attr override"]
    dcore --> locate
    sman --> locate
    pprod --> locate

    sman -->|borrows the collect-only boot| pprod
    dcore -->|describes records as| pdoc

    dcore -->|isolated dry boot| harness["spoc.testing scopes"]
    pprod -->|isolated dry boot| harness
    dcore --> kernel["Kernel public API<br/>start · registry · resolve · typed errors"]
    pprod --> kernel
```

`spoc.stubs` is the fifth contained subpackage. Its product is a `.pyi` beside the
project's composition root, which narrows `resolve` per identifier. A stub never
executes, so naming one app's classes for the type checker adds no runtime coupling
between apps — the decoupling the registry exists to provide survives being described.
`spoc.locate` sits outside every subpackage because they all need it and only
`spoc.cli` may import them.

`spoc.projection` is the sixth, and the only one that is also depended *on*. It owns
the collect-only boot — discovery runs, initialization does not — so a project whose
startup hooks would fail is still describable, and it owns the single description of a
registered component. Both other describing surfaces read that description rather than
building one: the stub adds the static type each identifier yields, which is meaningful
only to a type checker, and `spoc list` renders the same records as prose after a full
boot. One registry, one description, three renderings; the boot depth and the rendering
are the whole of the difference between the commands.

The findings never rephrase anything: `check` reports the kernel's own error
text (failing segment, valid candidates), gathered instead of raised. The
kernel imports none of this — `spoc.cli` is entry-point metadata until the
console script runs.

## Invariants

1. **Zero runtime dependencies** — anything needing a dependency is, by
   definition, not kernel. `dependencies` is empty, so installing spoc acquires
   nothing, and this holds for the shipped scaffolder too: every build-vs-adopt
   decision behind it landed on the standard library. The `spoc.formats`
   surface adopts packages, but every one is quarantined behind an extra and
   imported lazily — a bare install still acquires nothing.
2. **Describes, never executes** — the kernel calls no user code beyond
   lifecycle hooks; resolution is a pure lookup.
3. **One registry, one grammar** — all views are derived from the flat
   store; no second identifier scheme exists.
4. **Loud registration** — a declared component that cannot register fails
   startup with a precise error; nothing is silently dropped.
5. **Dependencies point inward** — the core imports nothing outside itself and
   performs no I/O; the loader never sees a registry; the config adapter only
   reads files. Every crossing is wired in `Framework` and nowhere else.
6. **One declaration point** — every attribute of a kind lives on its
   `KindSpec`. There is no decorator form and no parallel mapping, so a kind
   attribute cannot be stated away from the kind it describes.
7. **One metadata channel** — a record carries the metadata its kind declares
   and nothing else. A kind stating no contract accepts no metadata, so there is
   no untyped escape hatch by default.
8. **Boot leaves the process alone** — start mutates neither `sys.path` nor the
   filesystem; apps import through the normal import system under their declared
   dotted paths, and the only global a boot populates is Python's own module
   cache (which is why restart re-runs discovery, never module-level code).
9. **A stated concurrency contract** — registration is atomic under one lock,
   lifecycle transitions are serialized with exactly one winner, and reads
   between a completed start and a shutdown need no coordination. Shutdown ends
   that window and a read racing it is not covered: reset swaps in a fresh
   registry rather than emptying the live one, so such a read still observes one
   whole registry, but which of the two it observes is a race the caller must
   order itself. One object, one identity: divergent re-registration raises.
   The contract covers *derived* reads too, not only records: a failed `resolve`
   is composed from one observation of the store, so it never names a candidate
   that did not exist when the lookup ran, and a lifecycle phase groups the
   store once for every hook it dispatches, so two hooks in one phase never read
   two different registries — which is also what keeps a phase linear in a
   project's size rather than quadratic.
10. **A stated load order** — modules load, discover, and initialize in one
    total order: the rank of a kind in the declared `depends_on` order, then the
    position of the app in the effective `[spoc.apps]` list. Kind rank comes from
    the declaration, so it is identical for every app and no absent optional
    module can shift it. A kind is therefore a **phase** that completes across
    every app before the next begins, and the app list only ever orders modules
    *within* a phase — which is why no declaration can ask for one app's later
    kind ahead of another app's earlier one. `graphlib` is kept for refusing a
    cycle, not for producing the order.
11. **The inert state is unconditional** — every transition out of `started`
    reaches the inert state, whether or not the app-authored code it invoked
    succeeded and whether or not the rollback of a failed boot succeeded. A
    failing `teardown()` still propagates unwrapped, but the framework is
    restartable rather than stuck reporting itself started. Resetting kernel
    state and clearing the started flag are one operation for exactly this
    reason: as two steps, one of them was skipped.

    The cost is stated rather than hidden: a `teardown()` that raises aborts the
    walk, so modules behind it are not torn down and — because the loader is
    discarded by the reset — never will be. That is a resource leak, chosen over
    the alternative of swallowing failures or reporting them as a group, which
    would break the promise that the caller sees the exact exception the app
    raised. Fix the failing teardown; the kernel will not paper over it.
12. **The synchronous path refuses coroutines before running anything** — it
    establishes that no hook or module function it is about to run is a
    coroutine, and names every one it finds, before invoking the first. A
    coroutine declared by the last module in load order therefore costs no
    earlier module's side effects.
