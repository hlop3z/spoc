# Design: rename `meta` to `metadata`

## Context

`Component.metadata`, `KindSpec.metadata`, and `Internal.metadata` all spell the concept
`metadata`; only the registration keyword (`component(..., meta=)`, `@handle(meta=)`)
spells it `meta`. The main spec (`framework-declaration`) already speaks only of
"metadata" — the code deviated from the spec's vocabulary, not the reverse. The 1.0 tag
is uncut, so the pre-1.0 allowance covers the break.

## Goals / Non-Goals

**Goals:**

- One spelling — `metadata` — everywhere the concept appears: kwarg, fields, spec,
  docs, tests.
- Land before the 1.0 tag is pushed, while the break is free.

**Non-Goals:**

- No deprecation shim or dual-accept window (`meta=` alias). Nobody depends on SPOC
  yet; a shim would be dead compatibility code from birth.
- No renaming of the fields to `meta` (rejected — see Decisions).
- No behavior change of any kind: the metadata contract check, error types, and
  registry record are untouched.

## Decisions

### Direction: kwarg follows the fields, not the reverse

Renaming the fields `metadata` → `meta` was rejected for three reasons:

1. `Component.metadata` feeds the registry projection, whose document shape is a
   `public`-tier element (`schema:projection/document`). Renaming the field breaks a
   published JSON Schema contract for zero gain.
2. The stdlib precedent is `metadata` (`dataclasses.field(metadata=...)`,
   `importlib.metadata`).
3. Blast radius: kwarg direction is ~8 source lines + 5 test sites + 2 docs pages;
   field direction touches the projection, the stubs emitter, and a published schema.

### No build-vs-adopt decision needed

A rename introduces no tool, dependency, or critical concern; `/ai:decide` has nothing
to record. The existing gates (`apidiff`, `apicheck`, `spoc stubs --check`, docs
snippet suite) verify the result — nothing new is built.

### Internal names follow

`check_metadata(spec, obj_name, meta)` and the registrar closure's `meta` parameter are
internal, but the point of the change is that the word appears zero times in the
declaration layer afterward. Grep for `\bmeta\b` under `src/spoc/core/` must return
nothing when done.

## Risks / Trade-offs

- **Surface break pre-tag**: `apidiff` will report an incompatible change; per
  `release-policy` it reports without failing until 1.0. If the tag lands first, this
  change's cost jumps to a major release — sequencing is the mitigation.
- **Committed conformance fixture**: if the fixture's generated stub spells `meta=`,
  `spoc stubs --check` fails until regenerated. The task list orders regeneration
  before the gate run.
- Docs prose in `api/errors.md` shows `@view(meta=Route(path=…))` inside a table cell —
  the docs snippet suite does not execute table cells, so this site is caught only by
  grep, not by a gate. The task list uses grep sweep, not gate-trust, for docs.
