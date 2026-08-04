# SPOC — kernel architecture

What **is**, as of the framework-object API. SPOC is a registry-first
runtime kernel: one `Framework` object declares the kind set, apps declare
components inward, surfaces project outward from the registry, and every
dependency points at the kernel — never out of it.

## The shape

```mermaid
flowchart TB
    subgraph surfaces ["Surfaces — thin adapters (not part of SPOC)"]
        direction LR
        fastapi["FastAPI / Robyn<br/>HTTP"]
        cli["CLI"]
        workers["Workers / events<br/>(e.g. an execution engine app)"]
    end

    subgraph kernel ["SPOC kernel — zero runtime dependencies"]
        direction TB
        framework["Framework<br/><i>declaration + composition root</i><br/>kinds · kind() decorators · on_ready"]
        config["Config<br/>spoc.toml only · mode cascade"]
        importer["Importer<br/>load · cache · lifecycle"]
        discovery["Discovery<br/>markers → records, loud failures"]
        registry[("Registry<br/>flat store of Component records<br/>kind : namespace . object_name")]

        framework -- "start(base_dir)" --> config
        framework --> importer
        importer --> discovery
        discovery --> registry
        registry -. "on_ready(registry)" .-> framework
    end

    subgraph apps ["Apps — the domain (apps/ directory)"]
        direction LR
        blog["blog/<br/>models.py · views.py"]
        shop["shop/<br/>models.py · views.py"]
    end

    surfaces -- "enumerate · resolve<br/>(read-only, public API)" --> registry
    apps -- "declare<br/>@model = framework.kind('models')" --> discovery
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
