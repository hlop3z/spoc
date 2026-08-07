## Context

The origin record was introduced by `remote-template-sources` (archived
`2026-08-07`). Its values are computed by the scaffolding operation for every generation —
`operations.py:75-81` binds `template_reference`, `template_revision`, and `template_set_name`
whatever the set's origin — but the file only reaches disk because the built-in manifest declares
`spoc-template.toml.tmpl` among its files. Emission is therefore delegated to the very party the
record describes.

Two consequences, both live today:

1. A template set that omits the declaration produces a project with no record. Verified against
   a real remote generation.
2. A template set that *includes* a declaration is free to write whatever it likes there. Nothing
   stops a retrieved set from claiming a benign origin, because the record is ordinary rendered
   content and `values` hands it the true reference to interpolate — or to ignore.

The second is the sharper problem, and it is the reason the fix is "the operation authors the
record", not "every set must declare it". The record's purpose is to describe a template set to
a later operation; a description a subject can author is not a description.

Constraints this design works within:

- The core (`core.py`, `plan.py`) is pure — standard library and the kernel's identity grammar
  only. Everything is validated before a byte is written; a raised error means nothing reached
  disk.
- Template content is data in files of its own format, loaded through an adapter, never a string
  literal in code (`.canon/guidelines.md`). The record is emitted content, so the rule applies to
  how it is produced: a serializer over a data structure, never a format hand-assembled in code.
- `dependencies = []`. The base install carries no runtime dependency, and extras are feature
  flags rather than a way to make a base command work.
- The record is advisory throughout: nothing reads it at runtime, no operation fails because it is
  absent, unreadable, or disagrees (`template-provenance` Purpose). This change hardens *who
  writes it*, not *what depends on it*.
- Greenfield — no external template set exists, so no compatibility burden.

## Goals / Non-Goals

**Goals:**

- Every generated project carries an origin record, whatever set was rendered and whoever wrote
  that set.
- The record's content originates only from how the reference was resolved. No template set can
  suppress, forge, or substitute into it.
- The record survives every value a caller can legitimately supply — including a Windows path
  reference, which it does not survive today.
- The record's shape is defined once, on both the write and read side, next to itself.
- Answer and close the three open questions carried over from `remote-template-sources`.
- A remote failure names what the caller typed.
- Docs and behaviour agree in the same change set (Rule 8).

**Non-Goals:**

- Making the record load-bearing. It stays advisory; nothing starts reading it at runtime, and
  no operation gains a failure mode that depends on it.
- `spoc update`, cache eviction, private-repo auth — deliberately still out of scope.
- Signing, hashing, or otherwise attesting the record's content. Integrity here means "the
  scaffolder wrote it", not "the record is tamper-evident after the fact"; the record is a note
  in a directory the author owns and can edit freely.
- Changing what `add_app` does on divergence (see D5).

## Decisions

### D1 — The record is authored by the operation, not declared by the set

`init_project` contributes the record to the plan itself, after `build_plan` has rendered the
template set and before conflict detection and commit. The record is a `PlannedFile` like any
other, so it inherits never-overwrite and all-or-nothing unchanged — the existing
`template-provenance` scenario "The record is ordinary generated content" keeps holding for free.

*Alternatives considered:*

- **Require every set to declare it.** Validation could refuse a set that omits the record. It
  fixes suppression but not forgery, and it taxes every third-party author with a file they did
  not ask to own. Rejected.
- **Inject a synthetic `TemplateFile` into the loaded set before `build_plan`.** Tempting because
  it reuses the rendering path, but it keeps the three record-only values in the substitution
  vocabulary — which means `validate_template_set` still demands every set declare them, and any
  set's template can still interpolate them. It preserves exactly the coupling this change
  removes. Rejected.

The three record-only values consequently leave `values` in `operations.py` and leave the
built-in `manifest.toml`. They were never meant to be a template-set feature; they existed only
to feed the record, and now the record is fed directly.

`add_app` does **not** contribute the record: it adds to a project that already has one, and
rewriting it would overwrite an authored file — which the sink refuses anyway. Only
`init_project` writes it.

### D2 — The record is JSON, written by the standard library

**BREAKING for the record's own format**: it becomes `.spoc-template.json`, serialized with
`json.dumps` and parsed with `json.loads`. Approved via `/ai:decide`; recorded as
"Origin record serialization — Adopt the standard library (`json`)" in `DECISIONS.md`, which
supersedes the earlier "TOML writing — not needed, dissolved by scope".

The reason is a second live defect this gate surfaced. The record's values are arbitrary
caller-supplied strings, and interpolating them into TOML is serialization, not substitution —
the existing template does neither escaping nor quoting:

```
reference = "C:\templates\mine"   → TOMLDecodeError: Unescaped '\'
reference = "has"quote"           → TOMLDecodeError
```

`read_origin` treats a parse error as "no record" by design, so `spoc init` from a Windows
directory path silently produces a project with no provenance **today** — the same failure this
change exists to fix, arriving by a different route. Emitting TOML correctly would mean
hand-rolling escaping for a format on the never-hand-roll list, or taking `tomli-w` as a base
dependency for one advisory file. `json` is in the standard library, writes and reads, and its
escaping is not our problem.

What this costs: the record no longer matches the repo's TOML idiom, and JSON cannot carry the
comment header the template had — the explanation moves into a `note` field. The divergence
tracks a real line rather than blurring one: TOML is what a human authors here (`spoc.toml`,
`manifest.toml`), JSON is what the scaffolder writes for itself and reads back.

The record's content is therefore built as a data structure and handed to a serializer, which is
the adapter form "data is not code" asks for — no format is assembled in program code. Both
directions live in `provenance.py`, beside each other, so writer and reader cannot drift.

*Alternatives considered:* `tomli-w` 1.2.0 as a base dependency (correct serializer, MIT,
zero-dependency itself — but it overturns `dependencies = []` for one advisory file, and cannot
write comments either, so the header is lost regardless); a hand-rolled TOML escaper (~10 lines,
rejected on the never-hand-roll rule, which exists for exactly the bug above).

### D3 — The record's destination is reserved, enforced in the pure core

`validate_template_set` gains a third check alongside the two it already performs: a set
declaring a file whose rendered destination is the record's is refused with a new
`ReservedTargetError`, before anything is written. The reserved name has one definition —
`provenance.RECORD_NAME`, which already exists and is what `read_origin` looks for — and the core
imports it rather than restating it.

This runs in the pure layer beside `_reject_escape`, which is the existing precedent: a template
set is third-party content, and the checks that bound what it may do belong where they cannot be
defeated by a filesystem race.

Note the layering: D1 is what makes forgery impossible (the record never passes through the set's
rendering at all), and D3 is what makes an attempt to forge it *visible* rather than silently
ignored. Without D3 a set declaring the reserved target would simply lose to the appended record,
or collide confusingly; with it, the set is told what it did.

### D4 — Failures name the reference, not the derived location

`_get` in `remote.py` currently raises `RetrievalError(url, …)`, where `url` is what the adapter
constructed. It gains the `Reference` as a parameter and raises `RetrievalError(reference.raw, …)`,
carrying the derived location as reason detail. `Reference.raw` already exists and is documented
as "the reference exactly as supplied — used in errors, never to resolve"; this is the call site
that failed to use it.

### D5 — The three carried-over open questions, answered

**Does the record belong in the project's configuration file instead of its own file?**
No — its own file, and this is now a spec requirement rather than an implementation accident.
Merging it into the configuration would require the scaffolder to *edit* an authored file, and
"the project's configuration is never edited" is an existing guarantee `add_app` states in its
own docstring. A generated note and an authored configuration have different owners and different
lifecycles; one file each keeps that legible.

**Should the built-in set also record an origin, or is the record only meaningful for references
that can move?** It records one, unconditionally. A record present only sometimes makes the
divergence comparison partial, and trains an author to read "no origin recorded" as normal —
which is precisely how the current defect stayed invisible. The existing scenario "A set that
cannot move records no revision" already covers the shape: reference named, revision empty.

**Should `spoc app` refuse rather than warn when the recorded origin diverges and the kinds were
derived rather than stated?** No — it keeps warning. Refusing would make the record load-bearing:
deleting an advisory note would then change whether an operation succeeds, which contradicts
"nothing fails because it is absent" and would quietly turn the record into configuration. Two
implicit inputs disagreeing is worth a louder message, not a refusal. Closed, not deferred.

### Layering

Nothing moves across a boundary. `core.py` stays pure and gains one comparison. `provenance.py`
stays the module that owns the record's shape on both the read and the write side, and gains a
data file next to it. `operations.py` stays pure orchestration over ports. `remote.py` stays the
adapter and is the only place a URL is constructed or named. Dependencies still point inward: the
core learns a reserved *name*, never how that name is written.

### Build-vs-adopt verdicts

`/ai:decide` has run. Both concerns are **approved**; the full ADR blocks live in `DECISIONS.md`.

| Concern                                        | Tier                    | Verdict                                                                                              |
| ---------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------- |
| Serializing the record (never-hand-roll list)  | Adopt (standard library) | `json` — writes and reads, escaping is the stdlib's problem, `dependencies = []` intact. See D2.      |
| Record integrity against the template set      | Build by construction   | Values leave the substitution vocabulary, so no rendering path reaches the record. See D1/D3.          |

The second was the concern the proposal flagged; the first was found during the gate and
supersedes a standing ADR whose premise this change invalidates. Research also corrected an
assumption worth keeping: Copier writes `.copier-answers.yml` unconditionally and lets templates
only customize it — the mature tool in this space is a precedent for operation-authored emission,
and this design goes one step further by reserving the destination outright.

Adopting a whole generator was considered and rejected for both: it relitigates an approved
decision ("Project generation and template rendering — Build (thin)") and would add a runtime
dependency to a zero-dependency distribution.

## Risks / Trade-offs

- **A template set that legitimately wants to customize the record now cannot** → Intended, and
  it is the whole point: a description its subject can author is worthless. A set that wants to
  record its own metadata can emit any other file it likes.
- **An existing set declaring the reserved target starts failing** → Only the built-in set does,
  and this change removes that declaration in the same commit. No external set exists
  (greenfield). The failure is pre-write and names the reserved destination, so a future
  third-party author is told exactly what to remove.
- **Ordering bug: appending the record after `detect_conflicts` would skip its collision check**
  → The record must join the plan before `sink.is_empty()` and `detect_conflicts`. Covered by a
  task and by the existing "record is ordinary generated content" scenario, which a test must now
  exercise against the appended file rather than the rendered one.
- **`add_app` narrows a set with `replace(loaded, files=app_files, values=…)`** → It re-derives
  `values` from the app files' own identifiers, so dropping the three record values from the
  set-level declaration cannot destabilize it. Worth a test, not a redesign.
- **The record's filename changes, so any project generated before this change keeps a
  `.spoc-template.toml` nothing reads** → `read_origin` looks for the new name only; an old
  project reports "records no origin", which is the documented degradation and not a failure.
  No migration shim (greenfield — see the memory note on back-compat), but the old file is inert
  clutter in any project already generated, and the docs should say so rather than leave it
  mysterious.
- **Removing declared values is a template-set contract change** → Any set still declaring
  `template_reference` and friends will now fail `UnsatisfiedValueError`, since the operation no
  longer supplies them. Correct behaviour (the existing "unsatisfiable substitution" scenario),
  loud, and pre-write — but it must be called out in the template-authoring docs.

## Migration Plan

None required. No published template set outside this repository, no runtime consumer of the
record, no public API signature change. The built-in set's manifest edit and the record's new
authorship land in the same commit, so no intermediate state exists where the built-in set
declares a reserved target.

Rollback is a revert: nothing persists outside the generated project, and a generated project
carrying the record is unaffected either way.

## Open Questions

None. The three questions this change inherited are answered in D5 and written into the specs;
this change does not open new ones.
