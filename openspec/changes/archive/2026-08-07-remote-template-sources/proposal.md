## Why

A template set can only reach a user today by being installed as a Python distribution or by
already sitting on their disk. That makes every shared starter a release artifact — with a
version, a maintainer, and a dependency tree — which is the same model Yeoman used and the
reason it decayed into an unmaintainable ecosystem. A template is content, not a package, and
the kernel currently has no way to say so.

The practical cost is that a framework built on the kernel cannot put a single working command
in its README. `pip install some-template-package` before `spoc init` is a two-step install that
nobody completes, so downstream frameworks either vendor a copy of the scaffolder or tell people
to clone and copy directories by hand.

## What Changes

- A template set reference MAY designate a remotely retrievable location, in addition to the
  built-in set, an installed set, and a local directory.
- Reference resolution becomes **scheme-first and total**: every reference resolves to exactly
  one kind by an explicit discriminator, and an unresolvable one fails naming the segment that
  did not resolve. **BREAKING** for any reference containing a `:` that was previously read as a
  local path — a path-shaped discriminator is no longer the first branch tried.
- A retrieved template set is subject to the same validation, substitution, and never-overwrite
  guarantees as a local one. Retrieval failure, a malformed archive, or a rejected member path
  writes nothing.
- A retrieved reference is **pinned and cached by the exact revision it resolved to**, so the
  same reference generates the same project, repeat generations do not re-retrieve, and a
  previously retrieved revision remains usable without network access.
- A generated project **records the template reference and resolved revision that produced it**.
- Adding an app to a project whose recorded provenance differs from the template set being
  rendered surfaces that divergence rather than silently emitting a mismatched shape.
- The trust boundary becomes a **stated guarantee** rather than an internal property: generation
  never executes content carried by a template set, whatever its origin.

## Capabilities

### New Capabilities

- `remote-template-acquisition`: Retrieving a template set named by a remote reference — how a
  reference is parsed, pinned, retrieved, bounded, cached, and admitted or refused before any
  template set exists to validate.

  Critical concerns whose realization is a build-vs-adopt decision (deferred to `/ai:decide`):
  - **Archive member admission** — rejecting traversal, absolute paths, links, and special files.
    Security-sensitive; the equivalent code in a comparable framework has produced three separate
    path-traversal advisories.
  - **Resource bounds** — refusing an archive whose expanded size or member count is
    unreasonable, before expansion completes.
  - **Retrieval and redirect policy** — what a retrieval is permitted to follow, and what it must
    refuse to be redirected onto.
  - **Reference grammar** — an identifier scheme, therefore governed by Rule 9: adopt a
    recognized one rather than mint a private one.
  - **Cache location and keying** — where retrieved revisions live and how they are addressed.

- `template-provenance`: What a generated project records about its own origin, and how a later
  scaffolding operation against that project uses it.

### Modified Capabilities

- `scaffold-templates`: The requirement *A template set is replaceable* currently enumerates two
  resolvable forms (filesystem directory, importable package). It gains a third — a remote
  reference — and gains a total, ordered resolution rule in place of the present heuristic. The
  requirement *Substitution values are declared* gains the trust-boundary scenario for content of
  unknown authorship.

- `project-scaffolding`: *Generating a runnable project* gains the provenance record as part of
  what a generation emits. *Adding an app to an existing project* gains divergence reporting.

## Impact

- **Affected code**: `src/spoc/scaffold/` — reference parsing enters the pure core; a retrieval
  adapter and a cache adapter join the existing template-source and sink adapters; the
  `TemplateSource` port is reconsidered, since `available()` cannot be answered by a source that
  cannot enumerate. `src/spoc/scaffold/cli.py` gains no new logic but exposes the widened
  reference.
- **Dependency footprint**: unchanged and asserted. The requirement *The scaffolder does not
  alter the kernel's dependency footprint* (`project-scaffolding`) is a constraint on this
  change, not a casualty of it — no published dependency may be added, and the same holds for
  any external binary the kernel would have to shell out to.
- **Existing extension point**: the `spoc.scaffold_templates` entry-point group is unaffected and
  remains supported. This change removes the requirement that it be the *only* way to share a
  template set.
- **Generated projects**: gain one file they did not have before.
- **Network**: the kernel performs outbound network access for the first time, and only when a
  reference explicitly names a remote location. No other command acquires a network path.
- **Documentation**: the reference grammar and the stated trust boundary are user-facing surface
  and land in the same change set (Rule 8).
