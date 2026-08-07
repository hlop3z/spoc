## Context

The scaffolder resolves a template set reference in `InstalledTemplateSources.load`, today an
ordered `if`-chain of four branches: the built-in name, a separator heuristic that means "local
directory", an entry-point lookup, and a not-found error. The second branch is the problem — it
is a fallthrough dressed as a discriminator. Any reference containing `/` is read as a path, so
every remote reference form lands in `load_from_directory` and fails as a missing manifest at a
path the caller never typed.

Everything downstream of `load()` is already correct for this change and does not move: `core.py`
is pure, `_reject_escape` already treats template content as untrusted, `DirectorySink` stages to
a temporary directory and commits atomically, and validation is bidirectional and pre-write.
This change adds a stage *before* the existing pipeline, not inside it.

### Prior art consulted

Three findings shaped the decisions below.

**Django has shipped this feature and paid for it three times**, all three in archive handling
rather than in templating or transport: [CVE-2021-3281](https://security.snyk.io/vuln/SNYK-PYTHON-DJANGO-1066259)
(traversal via absolute paths and dot segments), [CVE-2025-59682](https://www.acunetix.com/vulnerabilities/web/django-relative-path-traversal-vulnerability-cve-2025-59682/)
(partial traversal via a shared common prefix — the `startswith` bug), and an
[August 2026 fix](https://www.djangoproject.com/weblog/2026/aug/04/security-releases/) for an
arbitrary file write where the `Content-Disposition` filename was passed to `os.path.join`.
The existing sink is structurally immune to the first two; the third is a rule this design must
state, because nothing in the current code has an opinion about it.

**The JavaScript ecosystem converged** — degit, then tiged, then giget (which powers `nuxi init`)
— on snapshot retrieval over cloning, host shorthands, and caching by commit. Cloning also leaves
a `.git` pointing at the *template's* history inside the user's new project, which is a UX defect
independent of any security argument.

**Yeoman is the counter-example**, and it is the model the kernel currently ships: templates as
installable packages. It decayed under its own dependency tree and
[Microsoft retired it in March 2026](https://spknowledge.com/2026/05/08/microsoft-spfx-cli-replacing-yeoman-2/).
The entry-point group stays, but it stops being the only door.

## Goals / Non-Goals

**Goals:**

- Reference parsing becomes a pure, total function in the core, testable with no network and no
  filesystem.
- Resolution becomes a dispatch on a parsed discriminator, not a growing `if`-chain.
- Retrieval, admission, bounding, and caching each sit behind their own port, so the test suite
  exercises the whole path without opening a socket.
- The published dependency set stays empty, and no external binary becomes required.
- A generated project knows where it came from.

**Non-Goals:**

- Updating an existing project when its template changes. The origin record is the prerequisite
  for it, deliberately laid now because it is cheap now; the operation itself is out of scope.
- Authenticated or private references. Retrieval carries no credentials and reads no credential
  store.
- Template composition, inheritance, or multiple sets in one operation. The existing rule stands:
  exactly one template set per operation.
- Signature or checksum verification of retrieved content beyond revision pinning.

## Decisions

### The seam: parsing is core, everything else is an adapter

```
 "gh:owner/repo@v1.2#subdirectory=templates/minimal"
                    │
     ┌──────────────▼───────────────┐
     │ parse_reference()            │  core · pure · stdlib only
     │   → Reference(kind, …)       │  no I/O, no network, no disk
     └──────────────┬───────────────┘
                    │
     ┌──────────────▼───────────────┐
     │ resolver dispatch on .kind   │  adapter
     └──┬────────┬────────┬─────────┘
        │        │        │
    builtin  directory  remote ──▶ Revision ──▶ ┌─────────┐ hit
    entry_pt                                    │  Cache  │────▶ TemplateSet
                                                └────┬────┘
                                                miss │
                                                ┌────▼────┐   ┌──────────┐
                                                │ Fetcher │──▶│ Admitter │──▶ cache ──▶ TemplateSet
                                                └─────────┘   └──────────┘
                                                  bytes         member-by-member

              dependencies point inward ◀──────────────────────────────
```

`Reference` is a frozen dataclass in the core beside `TemplateSet`. `Fetcher`, `RevisionResolver`,
and `Cache` are Protocols declared in the core alongside `TemplateSource` and `ProjectSink`; their
concrete implementations live in adapter modules and are wired in `spoc/cli.py`, which is already
the composition root and already injects `derive_kinds` the same way.

The payoff beyond tidiness: the grammar gets tested as pure function calls, and remote resolution
gets tested against an in-memory `Fetcher` rather than a live server or a threaded HTTP stub.

### Splitting the `TemplateSource` port

`available()` cannot be answered by a remote resolver — it exists to populate
`TemplateSetNotFoundError`'s candidate list, which is meaningful only for enumerable sources.
Stubbing it to `()` would put a lie in an error message.

`TemplateSource` keeps `load()`. Enumeration moves to a separate `EnumerableSource` protocol that
the built-in and entry-point sources implement and the remote resolver does not. The error
gathers candidates from whichever resolvers are enumerable, and for an unresolvable *remote*
reference reports the recognized reference forms instead — which is the actionable information at
that point anyway.

### Composition replaces the `if`-chain

`InstalledTemplateSources.load` dispatches on `Reference.kind` — a `match` over a parsed value
rather than a sequence of attempts that fall through to each other. `RemoteTemplateSource` is a
separate class holding the three retrieval ports, injected rather than imported, so the remote
path is absent unless something wires it. This is Rule 7: the chain was at four branches and
remote would have made it six.

> **Deviation from the original plan, recorded.** This was drafted as a separate `ChainedResolver`
> with `InstalledTemplateSources` demoted to one member. The implemented shape keeps the existing
> class as the dispatcher instead, because a new top-level type would have renamed the public
> surface (`spoc.scaffold.InstalledTemplateSources`, the docs' API page, and every call site) to
> buy nothing the `match` does not already give: form is still decided before existence, failures
> are still distinct, and candidates still come only from enumerable sources. The substance the
> plan was protecting is intact; the extra indirection was not paying for itself.

### Where the pipeline stops on failure

Retrieval, admission, and caching all complete before `build_plan` is called. `DirectorySink`
never sees a plan derived from content that was not fully admitted, so "nothing is written on
failure" needs no new enforcement — it is preserved by ordering. Staging to a temporary directory
during retrieval is not a violation of it: the guarantee is about the destination, and the sink
already stages the same way.

### Build-vs-adopt, per critical concern

Resolved by `/ai:decide`; every verdict is **approved** and recorded in full in `DECISIONS.md`.

| Concern | Verdict | One-line reason |
|---|---|---|
| Archive member admission | **Adopt + Extend** — stdlib PEP 706 filter, plus our own containment | The filter is the maintained standard (PEP 721 has pip extracting sdists with it), but it cannot stand alone: CVE-2025-4517 is arbitrary write via traversal *in `filter="data"` itself*, patched only in 3.12.11 / 3.13.4 while this project requires `>=3.12`. Re-verifying each materialized path makes that CVE inert on any patch level. |
| Containment check | **Extend** — existing `resolve().is_relative_to()` | Already in `DirectorySink`, already component-aware, already immune to the common-prefix bug. Now load-bearing rather than redundant — see the row above. |
| Resource bounds | **Build** (thin) | No stdlib API bounds *expanded* size, and the only OSS candidate covers zip but not tar — adopting it would break the invariant and still leave the tar path hand-written. Streaming counter, ~10 lines, the likeliest defect site in this change. |
| Retrieval and redirect policy | **Adopt + Extend** — stdlib transport, custom redirect handler | Transport is never hand-rolled; the invariant rules out `httpx`/`requests` for a shipped surface. Refusing scheme downgrade is a handler subclass of about a dozen lines — the same size under any client, so a dependency would buy ergonomics, not safety. |
| Reference grammar | **Adopt** — pip / PEP 508 direct-reference shape | Rule 9. Fluent to a Python audience, and the only candidate expressing both an archive reference and a revision-pinned VCS reference in one published vocabulary (`@ref`, `#subdirectory=`). `gh:` is sugar over it, not a parallel scheme. |
| Cache location | **Build** (thin) on the platform conventions | `platformdirs` is mature with no stdlib equivalent, but as a dependency it breaks the invariant and as an extra it reintroduces the two-step install this change exists to remove. Reading `XDG_CACHE_HOME` / `LOCALAPPDATA` / `~/Library/Caches` adopts the *conventions*, declining only the wrapper. |

Two of the six descend to Build. Both are justified by the same constraint rather than by novelty:
no option exists that covers the need without breaking the empty-dependency invariant, and in
both cases the adopted alternative would still leave the code written.

### Two rules stated because nothing in the code currently implies them

1. **No name used to build a local path may come from the remote party.** Temporary filenames are
   locally generated. `Content-Disposition` is not read. This is Django's third CVE, and it sits
   upstream of every path-escape layer the codebase already has.
2. **Bounds apply to expanded size, not transferred size.** A small transfer that expands
   enormously is the attack; checking the transfer length is checking the wrong number.

### The origin record is a template file, not a code literal

The record is emitted through the normal template mechanism as a declarative data file, so it
inherits never-overwrite, all-or-nothing, and appears in the printed file list like anything else
(Rule: data is not code). It must not affect whether the project starts.

## Risks / Trade-offs

- **The bounds check is hand-written in a change otherwise built on adopted parts** → It is the
  one concern with no mature stdlib answer. Isolate it in a single function with the bound as a
  named constant beside the concept it bounds, and test it with a crafted expanding archive rather
  than a real one.
- **The adopted extraction filter has itself had a critical bypass** →
  [CVE-2025-4517](https://www.wiz.io/vulnerability-database/cve/cve-2025-4517) (CVSS 9.4) was
  arbitrary filesystem write via traversal in `filter="data"`, patched in 3.12.11 / 3.13.4. This
  project's floor is `>=3.12`, so a supported interpreter may be vulnerable and we cannot control
  a user's patch level. Mitigated by not relying on the filter alone: every materialized path is
  re-verified with the component-aware containment predicate, which makes this bypass and any
  future one inert. The test for it must assert containment holds even when the filter is stubbed
  to pass everything, or it is testing the filter rather than our defense.
- **The scheme-first change is breaking for any reference containing `:`** → In practice this is
  a Windows drive-letter path (`C:\templates`). The parser must recognize a drive letter as a path
  form before treating `:` as a scheme separator, and this needs an explicit test on Windows,
  where this project's primary development happens.
- **The kernel acquires outbound network access for the first time** → Confined to one adapter,
  reachable only from a reference that explicitly names a remote location, and absent from every
  other command. Worth stating in docs rather than leaving for a user to discover.
- **Cache growth is unbounded over time** → Keyed by immutable revision, so it is never
  incorrect, only large. No eviction in this change; if it becomes a complaint, eviction is a
  contained follow-up that cannot affect correctness.
- **A retained revision makes a compromised-then-fixed template sticky** → Revision pinning means
  a retained bad revision stays retained. Acceptable: the user named that revision, and the record
  written into their project says which one.
- **Provenance is a new file in every generated project** → Some users will delete it. The spec
  requires the project to remain runnable without it, and divergence reporting degrades to
  "origin unknown" rather than failing.

## Migration Plan

No data or API migration — the kernel has no released consumers of the resolution path being
changed, and every existing reference form keeps working. The scheme-first parser is the only
behavioral change to existing inputs, and it changes only references containing `:`, which
previously could not resolve to anything useful except a Windows drive path.

Rollback is removal of the remote resolver registration: the chain falls back to the built-in,
entry-point, and directory resolvers with no other edit.

## Open Questions

- Should `spoc app` refuse rather than warn when the recorded origin diverges and `--kinds` was
  also derived rather than stated? Two implicit inputs disagreeing may warrant more than a
  message. Deferred until the warning exists and is seen in use.
- Does the origin record belong in the existing configuration file rather than its own file?
  Its own file keeps the configuration byte-identical under `spoc app`, which is an existing
  guarantee — but it is one more file in a scaffold that aims to be small.
- Should the built-in template set also record an origin, or is the record only meaningful for
  references that can move? Recording it unconditionally is simpler and makes the divergence
  comparison total.
