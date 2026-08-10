## Context

`spoc.scaffold` exposes 49 names. 27 of them carry the provisional notice, and they are
every provisional element in the distribution — the kernel (`core`, `framework`, `formats`,
`testing`, `diagnostics`) has none. The scaffolder's surface was never decided; it was
exported as it was written, and the notice was applied as a hedge rather than as a
judgement.

Two mechanisms already exist and are not being rebuilt here. `apicheck` derives every
tier from the source — exposure from a published namespace makes an element `public`, the
notice makes it `provisional`, submodule-only makes it `internal` — so changing a tier
means changing the source, never a list. `apidiff` compares the working tree's surface
against the last release tag and reports additions, removals, and tier movements. Both are
wired into `.canon/checks.md`, `Taskfile.yml`, and CI.

The pre-stable allowance in `release-policy` permits a `public` element to change
incompatibly in a minor release until 1.0 is cut. That allowance is what makes this change
cheap, and it is spent the moment 1.0 ships.

## Goals / Non-Goals

**Goals:**

- Assign every one of the 49 exposed elements an intended tier for the stable release, by
  applying the admission rule the spec delta adds rather than by taste.
- Leave `provisional` populated only by elements whose openness is a recorded judgement,
  each stating what would settle it.
- Exercise the deprecation lifecycle on a real element, so the stable-release criterion is
  met by evidence.
- Give the surface an admission rule, so this decision does not have to be repeated.

**Non-Goals:**

- No behaviour change to `spoc init` or `spoc app`. Nothing about generation, template
  resolution, retrieval, or the origin record's content changes.
- No kernel surface changes. The kernel is already fully `public` and is out of scope.
- Not cutting 1.0. This closes one criterion and produces evidence for another; the
  release is a separate decision.
- No new dependency. `dependencies = []` is unaffected.

## Decisions

### The admission rule is applied mechanically, not negotiated per element

Each of the 49 elements is tested against the four admissible reasons in the spec delta:
an operation invoked, a contract implemented, a condition distinguished *in order to
respond differently*, or a value supplied or read. Failing all four means the element
exists so the package can assemble itself, which the rule places at `internal`.

The decisive discriminator turned out to be **parameter position**. A port that appears in
the signature of `init_project` or `add_app` cannot be avoided by a caller — they must
name it to call the operation. A port that exists only to construct one of the package's
own adapters is composition. That line falls cleanly through the port set:

| Port | Appears in a public operation's signature | Tier |
|---|---|---|
| `TemplateSource` | yes — `init_project(source=…)` | public |
| `ProjectSink` | yes — `init_project(sink=…)` | public |
| `RevisionResolver`, `Fetcher`, `Cache` | no — only to build `RemoteTemplateSource` | internal |

`Reference` and `ReferenceKind` follow the second group: they are the vocabulary those
three ports speak, and nothing a caller passes to a public operation mentions them.

**Alternative considered**: keep every port public on the argument that ports exist to be
substituted. Rejected — substitutability is a property of the architecture, not evidence
of a consumer. Under that reasoning every `Protocol` in the package is public, which is
how the surface reached 49 names.

### Errors are exposed only where the distinction changes what a caller can do

`ScaffoldError` is exposed because one `except` clause catching everything the scaffolder
raises is the common case. Four leaves are exposed because each admits a distinct response:

| Error | The different response it enables |
|---|---|
| `TargetNotEmptyError` | choose another destination and retry |
| `TemplateSetNotFoundError` | offer the caller the sets that do exist |
| `UnrecognizedReferenceError` | correct the reference's spelling |
| `RetrievalError` | fall back to a local set, or retry |

The remaining ten (`PathConflictError`, `PathEscapeError`, `IncompleteTemplateSetError`,
`UnsatisfiedValueError`, `UndeclaredValueError`, `ReservedTargetError`,
`InsecureRedirectError`, `MemberRefusedError`, `BoundExceededError`,
`RevisionUnavailableError`) all mean "the input or the retrieved content is bad, report
it". A caller distinguishing them changes only the wording of a message it did not write,
so they stay reachable from `spoc.scaffold.errors` and promise nothing.

**Alternative considered**: expose all fifteen, since error classes are cheap to keep
compatible. Rejected — cheap is not free, and "we might as well" is the reasoning the
admission rule exists to refuse. They remain importable; reaching an internal element is
already specified as not a promotion.

### The provenance split: reading is public, writing is the operation's own business

`Origin`, `read_origin`, and `RECORD_NAME` answer "where did this project come from",
which a consumer that never generates anything can legitimately ask. `record_content`,
`record_file`, and `describe_divergence` are how `init_project` and `add_app` produce and
compare the record; a caller reaches none of them, and `AddedApp.divergence` already
carries the only result of the comparison a caller needs.

### Four elements stay provisional past 1.0, each with a stated settling condition

The spec delta requires a provisional element to state what would settle it, so the tier
is a judgement rather than a hedge.

| Element | What would settle it |
|---|---|
| `Origin`, `RECORD_NAME`, `read_origin` | whether the origin record must also carry the substitution values a generation used. The question was raised when `spoc update` was considered and declined; the record's shape cannot be promised until it is answered. |
| `EnumerableSource` | whether any template source outside this package implements it. It refines `TemplateSource` for one purpose — contributing candidates to a not-found error — and no external implementer exists yet. |

### The lifecycle is exercised on one element, not on all twenty-six

The pre-stable allowance permits withdrawing a `public` element in a minor release without
the deprecation lifecycle, so twenty-five withdrawals take that route. But the stable
criterion demands the lifecycle be *exercised*, and only a real deprecation is evidence.

`extract_archive` is the element chosen. It is a genuinely standalone, useful function —
bounded, containment-checked archive extraction — which makes it the most plausible thing
a consumer would have imported, and its migration is exact rather than approximate. It
keeps working from `spoc.scaffold` for one minor release, signals deprecation when reached
there, and is removed from the published namespace at 1.0.

Keeping all twenty-six as deprecated re-exports was considered and rejected: it buys the
same evidence at twenty-six times the machinery, and this project deletes compatibility
shims rather than accumulating them. One is enough to demonstrate a lifecycle; the rest
are covered by the allowance the policy publishes.

### The deprecation signal attaches to the re-export, not to the definition

The signal must fire when `extract_archive` is reached through `spoc.scaffold`, and stay
silent when it is reached through `spoc.scaffold.archive` — that is precisely the
migration being asked for. Decorating the definition itself would warn on both paths and
punish the correct one.

The re-export is therefore *decorated* rather than eagerly re-exported: the package binds
the name to the already-adopted PEP 702 decorator applied to the submodule's function. The
existing deprecation-signal decision governs what the signal is; this decision governs only
where it is attached.

A module-level attribute hook (PEP 562) was the first choice and was rejected at the
build-vs-adopt gate. It preserves object identity across both paths, but a dynamically
served name is invisible to static analysis: type checkers cannot see the PEP 702
deprecation, and neither can griffe — so `apicheck` would report the element as already
withdrawn rather than as present-and-deprecated. The whole purpose of this exercise is
producing *demonstrated* evidence for a stable-release criterion, and evidence the
project's own surface tooling cannot see is weak evidence. The decorated re-export costs
object identity between the two paths, which nothing here depends on, and buys visibility
in both the type checker and `apicheck`.

### Core, adapters, and where the wiring lives — unchanged

This change moves no code between layers. `plan.py` remains the pure core naming the
ports; `sink.py`, `sources.py`, `remote.py`, `cache.py`, `archive.py` remain the adapters;
`cli.py` remains the composition root and is the one internal caller whose imports must be
checked against the narrowed namespace. Dependencies continue to point inward. What
changes is only which of these names the package's published namespace re-exports.

### Build-vs-adopt decisions

Recorded by `/ai:decide`. Two concerns in this change are already governed by approved
ADRs in `DECISIONS.md` and are referenced rather than re-decided; two are new.

#### Decision: Deprecated re-export mechanism — Build (thin) on the adopted PEP 702 decorator

- **Status**: approved
- **Why**: the signal must distinguish the two import paths, and it must be visible to the
  tooling that produces this change's evidence. Binding the package name to
  `deprecated(...)` applied to the submodule's function gives a runtime warning on the
  withdrawn path only, static-checker visibility through PEP 702, and a real element for
  griffe to see — so `apicheck` reports it as present-and-deprecated rather than gone. It
  is one line against machinery this project already adopted and isolated.
- **Considered**: a PEP 562 module attribute hook (preserves object identity, but a
  dynamically served name is invisible to both type checkers and griffe, which would make
  the lifecycle evidence unobservable to the project's own gates); adopt `lazy-loader`
  (scientific-python, SPEC-0001 — maintained and purpose-built for attribute serving, but
  built for lazy imports rather than deprecation, carries the same static-visibility loss,
  and would put a runtime dependency into a distribution whose empty `dependencies` list
  is load-bearing).
- **Isolation**: `spoc.core.deprecation` remains the single import site for the decorator;
  `spoc/scaffold/__init__.py` is the only place the binding appears.

#### Decision: Settling-condition detection — Extend the adopted extractor (`apicheck`/griffe)

- **Status**: approved
- **Why**: the rule is that a provisional notice must carry prose beyond the boilerplate
  sentence. That is project-specific vocabulary no general tool can know; griffe already
  parses the docstrings the rule reads, and `apicheck` already derives the tier that
  selects which elements it applies to. Extending the existing extractor adds a predicate,
  not a mechanism.
- **Considered**: adopt a docstring linter (`ruff`'s pydocstyle rules, `pydoclint`) — they
  check docstring *form*, not the presence of a project-defined clause, so the rule cannot
  be expressed in them; declare settling conditions in a separate register — rejected
  outright, the contract requires the tier be determinable from the artifact alone.
- **Isolation**: the predicate lives beside the notice constant in `apicheck.core`, with
  its limitation stated there.

#### Decision: Tier derivation and cross-release comparison — Adopt griffe *(referenced)*

- **Status**: approved, unchanged
- **Why**: already decided in `DECISIONS.md` under *Public API surface extraction*. This
  change consumes both `apicheck` and `apidiff` and alters neither's mechanism.
- **Isolation**: `scripts/py/tools/apicheck/`.

#### Decision: Deprecation signal — Extend PEP 702 *(referenced)*

- **Status**: approved, unchanged
- **Why**: already decided in `DECISIONS.md` under *Deprecation signal*. This change is
  the first consumer of that machinery, which is the point: the criterion asks for the
  lifecycle to be exercised, and a decision recorded but never used is not evidence.
- **Isolation**: `spoc.core.deprecation`.

## Risks / Trade-offs

- **The decorator stamps the definition as well as the re-export** → *confirmed during
  implementation, and mitigated.* Both the standard library's `warnings.deprecated` and
  this project's 3.12 fallback set `__deprecated__` on the object they are given as well as
  on the wrapper they return, so decorating the definition would mark the very import path
  the migration recommends. The re-export therefore forwards through a throwaway function —
  `spoc.core.deprecation.deprecated_alias` — which takes the mark instead. The definition
  is left unmarked, and both halves are asserted in the tests.

- **Neither gate models deprecation** → *observed during implementation; the design's
  prediction was half right.* `apidiff` does report the decorated re-export as
  `spoc.scaffold.extract_archive (public)`, so the element is visible to griffe — which was
  the property that ruled out the dynamic alternatives. But neither `apicheck` nor
  `apidiff` has any concept of a deprecated element, so neither says that it *is*
  deprecated. The evidence that the lifecycle ran therefore lives in the code, its tests,
  and the changelog rather than in the gates' output. That is a real gap in a policy which
  requires a deprecation lifecycle and gates the surface: the check that enforces the
  contract cannot see the one mechanism the contract mandates. Left as scope for a later
  change rather than grown into this one — see Open Questions.

- **`extract_archive` becomes two objects** → `spoc.scaffold.extract_archive is not
  spoc.scaffold.archive.extract_archive` after this change. Nothing in the package or its
  tests compares the function by identity, and it is called for its effect rather than
  passed as a token, so the cost is accepted rather than mitigated. It is stated here
  because a reader who discovers it later would reasonably read it as a bug.

- **`apidiff` will report a large removal set** → 25 hard withdrawals plus tier movements
  against `v0.5.0`. Expected, permitted by the allowance, and reported without failing
  until 1.0. The risk is that a large expected diff trains us to skim it; each removal is
  therefore listed in `CHANGELOG.md` individually rather than summarized as a count.

- **The settling-condition check is weaker than the requirement it enforces** → whether a
  notice "states what would settle it" is not mechanically decidable. The check can only
  require that the notice carries prose beyond the boilerplate sentence. That catches the
  actual failure mode — a bare hedge copied from element to element — and admits a
  settling condition that is present but vacuous. Accepted, with the limitation stated
  where the check is defined rather than left for a reader to discover.

- **A withdrawn element is still importable, and that reads as a distinction without a
  difference** → the tier rules already specify that reaching an internal element is not a
  promotion, and `spoc.scaffold.errors` remains a legitimate import path. The change is in
  what is promised, not in what is reachable; the documentation must say so plainly or the
  withdrawal will look like theatre.

- **Nineteen public elements is still a large surface for a subsystem the project treats
  as a convenience** → possibly. But each survivor now has a stated reason under the
  admission rule, which is the property that was missing. Trimming further is a later
  judgement the rule makes cheap to revisit.

## Migration Plan

No data or runtime migration — the kernel does not import from `spoc.scaffold`, and no
generated project imports it either. Internal importers are `spoc.scaffold.cli` and the
scaffold test modules; both move to submodule imports where a name was withdrawn.

For an external consumer, the migration is one line per name: import from the defining
submodule instead of the package. `extract_archive` keeps working through the deprecation
period and says so when reached the old way.

Rollback is restoring the export list. Nothing else in the change is load-bearing: the
notices are documentation, and the attribute hook is additive.

## Open Questions

- ~~Is `DirectorySink` public because a caller genuinely needs to construct one, or only
  because `init_project` currently requires a sink to be passed rather than defaulting to
  a destination path? A default would make both `DirectorySink` and `ProjectSink`
  avoidable for the common call. Not changed here — it is an operation signature change,
  not a surface decision — but it would shrink the public set by two if taken later.~~
  **Struck: the shrink is not available at a price worth paying.** Three things this
  question did not weigh, found by reading the code rather than the archive:

  `ProjectSink` cannot be demoted at all while it remains a parameter. This repository
  already recorded the governing rule for that case when it made `TemplateSource` public
  — "it is a parameter of `init_project`, so a caller cannot avoid naming it"
  (CHANGELOG, remote-template entry). The same sentence decides `ProjectSink`, and it is
  a surface rule, not a preference.

  The signature change the question proposes breaks Rule 2. `operations.py` states the
  injection as deliberate in its own module docstring — the operation takes ports rather
  than constructing them so it stays testable without a filesystem. Any default, for
  `sink` or `source` alike, imports an adapter (`os`, `shutil`, `tempfile`,
  `importlib.metadata`) into the pure core and inverts the one dependency direction the
  rule fixes. A public-name count of two does not buy that.

  A facade module beside `cli.py` would keep the layering and get the DX, and was
  rejected as speculative generality: it adds a public name, withdraws the "callable
  from a downstream framework's own entry point" promise `operations.py` makes, and
  duplicates the composition root the CLI already is — for an embedder that does not yet
  exist. The call-site noise is real but falls on the embedding API, not on `spoc init`.

  Nothing to do. If an external tool ever embeds the scaffolder and finds the wiring
  costly, reopen it then with a real implementer's shape to fix, the way
  `EnumerableSource` is written to settle.
- ~~`AddedApp` is public as `add_app`'s return type, while `GenerationPlan` is public both
  as a return type and as the thing `AddedApp` carries. If the operations later return a
  single result type the two would merge; nothing here depends on that.~~ **Struck with
  the item above**, on which it was always conditional. The two types would merge only
  under the facade that was rejected; absent it they stay distinct because the operations
  genuinely return different things — `init_project` reports what was written,
  `add_app` reports what was written, where it landed, and what to tell the author.
- ~~**Should `apicheck` report deprecated elements?** Discovered while implementing: neither
  gate models deprecation, so a `public` element that has entered the withdrawal lifecycle
  is indistinguishable from one that has not. `release-policy` requires the lifecycle and
  requires the surface assertion to be checkable rather than asserted by hand; those two
  requirements do not currently meet. griffe already reads `__deprecated__`, so the cost is
  small. Deliberately not taken here — it is a second extension to `apicheck` in a change
  that already has one, and this change's own criterion is met by the tests. It should be
  its own change before 1.0 is cut, since 1.0 is the release at which the pre-stable
  allowance ends and the lifecycle stops being optional.~~ **Resolved by
  `enforce-deprecation-lifecycle`, the very next change.** The gate models deprecation as
  `Withdrawal` on `Exposure` — deliberately not a fourth `Tier`, so a marked element keeps
  every promise its tier makes until the release that removes it. Malformed marks are fatal
  (`unreplaced-withdrawal`, and `unsanctioned-withdrawal` for a signal raised outside
  `spoc.core.deprecation`); removals are judged by `lifecycle_verdict`, fatal from 1.0.
  Two guesses here were wrong and are worth naming: it landed in **`apidiff`, not
  `apicheck`** — `_in_flight` lists every element marked but still exposed, with its tier,
  over the whole surface rather than the delta — because the withdrawal inventory belongs
  beside the lifecycle enforcement, not beside the contract assertion. And the signal is
  **PEP 702 `@deprecated` through one sanctioned module**, not griffe reading
  `__deprecated__`; see DECISIONS.md. Nothing remains to do, and no 1.0 prerequisite
  survives from this question.
- **PEP 842 (Module Exports)** — draft, targeting Python 3.16, created July 2026 — proposes
  an `export` statement, an `__export__` collection, a `from … export …` re-export form,
  and an `ExportWarning` emitted when an unexported module attribute is reached. That is a
  language-level expression of exactly what the admission rule in this change states in
  prose, and of the "internal but still importable" position the withdrawn elements occupy.
  Nothing can be built on a draft, and the floor here is 3.12. Recorded so the rule is
  revisited against the standard if the PEP lands (Rule 9), rather than diverging from it
  by inattention.
