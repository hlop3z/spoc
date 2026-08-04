# SPOC — kernel architecture

What **is**, as of the kernel collapse. SPOC is a registry-first runtime
kernel: one `Framework` object declares the kind set, apps declare components
inward, surfaces project outward from the registry, and every dependency points
at the kernel — never out of it.

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
            loader["loader<br/>import · dep order · lifecycle<br/><i>kind-blind</i>"]
            config["config<br/>spoc.toml only · mode cascade"]
        end
    end

    subgraph apps ["Apps — the domain (apps/ directory)"]
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
    ns["namespace<br/>= app package name"]
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

## Invariants

1. **Zero runtime dependencies** — anything needing a dependency is, by
   definition, not kernel. This holds for the shipped scaffolder too: every
   build-vs-adopt decision behind it landed on the standard library, so the
   published wheel declares no `Requires-Dist` at all.
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
