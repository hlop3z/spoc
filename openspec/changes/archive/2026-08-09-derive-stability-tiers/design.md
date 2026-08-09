## Context

The stability contract shipped on 2026-08-08 with tiers declared in `[tool.spoc.stability]`
and enforced by `apicheck`, a static checker built on griffe that never imports `spoc`. That
design put the tier in a manifest and made the checker's job a set-difference: does the
declared surface equal the observed one.

Two things have become visible since.

**The manifest restates the source.** Measured against the current tree, two rules already
present in the code reproduce all 132 declared Python tiers, with zero mismatches, zero
missing, and zero extra:

```
  spoc/                     exposed from a package __init__  ->  public
   __init__.py              ... unless its docstring carries
   scaffold/                    the provisional notice        ->  provisional
     __init__.py
     cli.py                 exposed from a plain module only  ->  internal
     core.py
```

Concretely: all 20 `internal` entries are submodule-qualified paths (`spoc.testing.core.mode`,
`spoc.diagnostics.cli.register`) and all 27 `provisional` entries are `spoc.scaffold.*` names
that already carry the notice `apicheck` enforces. The manifest holds no fact the artifact
does not.

**The contract does not enforce itself across releases.** `apicheck` compares the declared
surface to the real surface at one point in time. Nothing compares this tree to the previous
release, so the compatibility promise a version increment asserts is unverified. The project
is at `0.5.0` with a `v0.5.0` tag, so a baseline exists to compare against.

A third fact constrains the design: the pre-stable allowance is in force until 1.0, and it
explicitly permits a `public` element to break in a minor release. A cross-release check that
fails on public breakage today would contradict the contract it is meant to enforce.

## Goals / Non-Goals

**Goals:**

- The tier of an importable element is a consequence of the artifact, readable from the
  artifact, with no list maintained beside it.
- `[tool.spoc.stability]` retains only what no static observer can see.
- The surface check verifies that the derivation resolves cleanly, rather than diffing a copy
  against its original.
- Surface change between releases becomes visible and, at 1.0, enforced.
- Adding a public name costs the two edits the language and its toolchain already require.

**Non-Goals:**

- Changing any element's tier. The tiers after this change are byte-identical to the tiers
  before it; only their home moves. Any tier change is a separate decision.
- Cutting 1.0, or ticking any 1.0 criterion. The deprecation lifecycle still has never run on
  a real element and this change does not run it.
- Touching `src/spoc`. No runtime code changes; the zero-runtime-dependency invariant is
  untouched, and every tool involved is a development-time gate.
- Replacing `apicheck`. It narrows; it does not go away, because the non-import elements still
  need an observer and the coverage-gap reporting is a spec'd requirement.

## Decisions

### The derivation rules are pure core; observation is an adapter

The rule *(exposed-from-a-package, carries-notice) → tier* is a total function over facts
about an element. It has no I/O and belongs in `apicheck.core` beside the tier vocabulary it
already owns. Determining *which* module exposes a name, *whether* that module is a package,
and *what* documentation the name carries is observation of an external system — the source
tree — and stays behind the existing `extract` adapter.

This inverts the current arrangement, where the rules live as data in a TOML file and the core
performs a set-difference. After the change, the core holds the policy and the adapter holds
the looking. The dependency direction is unchanged: `extract` and `packaging` depend on
`core`; `core` depends on neither.

`manifest` keeps its job — reading declared elements from configuration — but its input
shrinks to the non-import kinds and the `excluded` flags.

### Non-import elements stay declared, and the boundary is stated

Griffe documents that it cannot see console scripts, entry points, or extras. Those twelve
elements (`script:`, `entry-point:`, `extra:` ×5, `fixture:` ×3, `schema:`, `template-set:`)
have no definition site a static reader can attribute a tier to, so they remain explicitly
declared. This is not a gap being tolerated; it is the reason the manifest continues to exist,
and the spec now states which kinds are governed by rules and which are declared.

Note that three of the twelve — the pytest fixtures — *are* Python functions, but their
surface identity is the fixture name a consumer requests, not the importable path. They are
declared for that reason, not because they cannot be seen.

### The cross-release check reports before 1.0 and fails at 1.0

The pre-stable allowance permits incompatible `public` change in a minor release until 1.0.
Wiring a fail-closed breakage gate now would make CI contradict `release-policy`. So the check
runs from the start and always reports, but its failure condition is bound to the increment
being claimed and to the maturity in force — which is what the modified requirement says.

This also gives the unmet 1.0 criterion something to attach to: the first genuine deprecation
gets walked end to end against a check that can already see the element disappear.

### Growth of the surface replaces the manifest's friction

Today a new export fails CI until someone assigns it a tier — deliberate friction, recorded as
such. Deriving the tier removes it. The replacement is the cross-release comparison reporting
a newly exposed `public` or `provisional` element as an addition, so the promise is still a
reviewable event in the diff that creates it. The friction moves from "edit a second file" to
"the check names what you just promised", which is the same gate without the copy.

### The cross-release check is its own gate row and its own command

`.canon/checks.md` is one row per command, and the cross-release comparison is a different
command against a different input — the working tree versus a git tag, rather than the working
tree alone. Folding it into `apicheck` would put two unrelated failure modes behind one exit
code. It becomes its own row, its own command (`apidiff`), and its own exit code, and
`apicheck` stays narrow.

**Amended during implementation.** This section first said "not part of `apicheck`", meaning a
separate distribution. Implementation showed why that is wrong: the adopted differ reports
breakages but has no notion of additions, and the requirement that a newly exposed `public` or
`provisional` element be reported is what replaces the manifest's friction. Computing additions
means deriving the surface at both refs *with the same tier rules* — otherwise an element could
be announced at one tier while actually carrying another. A separate distribution would
therefore have to depend on `apicheck` for `derive_contract` and `exposures`, which is tighter
coupling than the git dependency it was avoiding. `apidiff` ships as a second console script in
the same distribution: separate command, separate row, separate exit code — every reason the
original decision gave — without a tool that exists only to import another tool's policy.

### The critical concerns are decided below

Both build-vs-adopt questions the proposal flagged are resolved in `## Decisions (ADRs)`.

## Decisions (ADRs)

### Decision: Cross-release breaking-change detection — Adopt `griffe check`

- **Status**: approved
- **Why**: it is the capability the existing griffe ADR already bought. That decision chose
  griffe partly because "`griffe check` classifies breaking vs compatible changes between refs,
  which `release-policy` needs to assert version increments" — the tool was adopted and then
  never wired. `griffe>=2.1` is already a declared dependency of `apicheck`; ISC, actively
  maintained, sponsored by FastAPI among others. It defaults to the latest tag, emits
  CI-native annotations (`-f github`), and covers a documented set of breakage kinds.
  Verified on this tree: `griffe check spoc -s src -a v0.5.0` exits 1 and reports
  `TemplateSource.available: Public object was removed` — a genuine breakage that shipped in
  the remote-template work and that no gate caught at the time. It ran with `spoc` absent from
  the tool environment, so the checker's no-import invariant survives.
- **Considered**: *AexPy* (MPL-2.0) — the only Python tool purpose-built for this, but a
  26-star research prototype from an ISSRE 2022 paper that dynamically imports the target
  module and needs its dependencies installed; that contradicts the no-import invariant
  outright and would require installing the extras in CI. *A snapshot differ over our own
  extracted surface* — cheap, since the extractor exists, but it reports only that something
  changed and never what kind, so the compatibility assertions stay unverifiable. Rejected
  without scoring: `docspec-python` (built on `lib2to3`, removed in Python 3.13) and
  `frappucino` (unmaintained).
- **Isolation**: its own gate row in `.canon/checks.md`, invoked as a command with the
  baseline ref as an argument. Nothing imports it; replacing it means editing one row, three
  places (the table, the Taskfile, CI) per the rule that table already states.

### Decision: Static tier derivation — Extend the existing `griffe` adoption

- **Status**: approved
- **Why**: every fact the rules need — which module exposes a name, whether that module is a
  package, and what documentation the name carries — is already on the objects the `extract`
  adapter walks. Verified before this design was written: the rules reproduce all 132 declared
  Python tiers exactly, with zero mismatches, zero missing, zero extra. Adding no second
  observer means there is never a question of which one is right.
- **Considered**: *Build on stdlib `ast`* — drops a dependency but re-implements `__all__`
  precedence and re-export/alias resolution, which is the reasoning the prior ADR already used
  to reject stdlib for extraction; the same argument applies unchanged. *A second static
  analyzer (`libcst`, pyright's JSON output)* — heavier, and puts two tools in a position to
  disagree about one fact.
- **Isolation**: the existing `extract` adapter grows the package-versus-module observation.
  The tier rules themselves are **not** griffe's concern and do not live there — they are
  project policy and belong in `apicheck.core` as a pure function, which is what keeps the
  adapter replaceable.

## Risks / Trade-offs

- **A tier becomes implicit, so an accidental export silently promises stability** → The
  cross-release check reports every newly exposed `public` and `provisional` element by name.
  The promise is still visible in review; it is simply not typed twice. This is the trade the
  recorded decision on manifest friction accepted, and it only holds if both halves of this
  change ship together — deriving tiers without the addition report would remove a gate and
  replace it with nothing.

- **The `provisional` rule matches on prose in a docstring** → Brittle in principle, but this
  is exactly how the shipped checker already detects the notice, so the change introduces no
  new fragility. The notice text is a single constant in `core`; the risk is bounded to
  keeping it one constant, and the rule-resolution check fails loudly if an element stops
  matching.

- **Derivation could disagree with intent for a name deliberately exposed at a package level
  but not meant to be public** → No such name exists today (132/132). Should one arise, the
  contract's own answer applies: the resolution is to move the element, not to annotate an
  exception. Adding an escape hatch to the manifest would rebuild the thing this change
  deletes.

- **Losing the manifest loses a human-readable inventory of the public surface** → The
  inventory becomes a generated view rather than a maintained file. Anyone wanting the list
  runs the check; the documentation page keeps describing the tiers and their guarantees,
  which is the part a consumer actually reads.

- **The baseline for comparison is a git tag, which assumes tags are pushed and complete** →
  Tags exist through `v0.5.0` and the repo is now in sync with the remote. The check must state
  plainly which baseline it resolved rather than silently comparing against nothing — a
  comparison with no baseline is the same trap as reporting "nobody looked" as "it is gone",
  which the coverage-gap requirement already forbids.

## Migration Plan

No consumer migration. Every element keeps its current tier, and the tier's new home is the
artifact consumers already read. `[tool.spoc.stability]` remains a valid section with the same
key names, so nothing that reads it breaks — it simply lists fewer elements.

The order that keeps every gate green at each step:

1. Teach the checker the rules and verify it reproduces the current manifest exactly, with the
   manifest still in place. This is a pure addition and can be asserted as a test.
2. Only once step 1 passes, delete the 132 Python entries.
3. Wire the cross-release check in report mode, before deleting anything that gated surface
   growth.

Rollback is restoring the deleted entries from git history; the derivation and the manifest
agree by construction, so the two forms are interchangeable at any commit.

## Open Questions

- **What is the baseline when no prior tag is reachable.** The adopted tool defaults to the
  latest tag, which resolves to `v0.5.0` here, and an explicit ref works. The unresolved half
  is CI: a shallow checkout has no tags, and a silent "no tags, nothing to compare" would pass
  green while checking nothing. The workflow must fetch tag history, and the check must state
  which baseline it resolved — report-with-no-baseline has to be distinguishable from
  report-with-no-changes, for the same reason the coverage-gap requirement forbids reporting
  "nobody looked" as "it is gone".
- **Whether `spoc.__version__` should be excluded from comparison**, since its value changes
  every release by definition and it is declared `public`. The `excluded` flags are the
  natural home if so.
- **What to do about the breakage already found.** `TemplateSource.available` was removed
  between `v0.5.0` and now. The pre-1.0 allowance permits it, so nothing needs reverting — but
  `release-policy` requires every release to record its surface changes, and this one is
  unrecorded. Recording it retroactively is arguably outside this change's scope; leaving it
  means the first run of the new gate reports a finding with no matching record.
