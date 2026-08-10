## Context

`apicheck` derives every importable element's tier from the source and `apidiff` compares
that surface against the previous release. Neither models withdrawal. `Exposure` carries
four facts — `element`, `from_package`, `documented`, `settling_stated` — and `Change` has
three members: `ADDED`, `REMOVED`, `RETIERED`. A search for "deprecat" across all seven
modules returns nothing.

The consequence is observable today:

```
spoc.scaffold.extract_archive | tier = public | provisional-notice = False
```

That is the one element in the withdrawal lifecycle, reported as an ordinary `public` name.

Three facts from exploration shape this design.

**The mark is not something the extractor already gets for free.** The archived
`decide-scaffold-surface` design recorded that "griffe already reads `__deprecated__`, so
the cost is small." It does not. In griffe 1.x, `Object.deprecated` is initialized to
`None` and assigned in exactly one place — the JSON decoder in `_internal/encoders.py`. The
static visitor never sets it; the attribute exists so that a `griffe dump` round-trips.
And our mark is not a PEP 702 decorator anyway, it is a module-level call:

```python
extract_archive = deprecated_alias(archive.extract_archive, "...removed at 1.0.")
```

which is statically an attribute assignment whose value is a call expression.

**Two points cannot answer a three-point rule.** `apidiff` holds the working tree and one
baseline tag. From those it can see that an element was present and marked before it
vanished, but not *when it was first marked* — which is what the waiting period is measured
from.

```
   v0.6.0            v0.7.0            1.0.0 / working tree
     |                 |                      |
     X marked          X marked               X gone
     |_________________|______________________|
       the rule needs all three; the tool holds the last two
```

**The clock has not started.** `v0.5.0` is dated 2026-08-06; `deprecated_alias` landed
2026-08-09 and sits under `[Unreleased]`. The mark first ships in 0.6.0, so this check can
be in place before there is any history for it to get wrong.

## Goals / Non-Goals

**Goals:**

- Model withdrawal as a fact beside the tier, throughout observation, comparison, and
  reporting.
- Establish the first-marking release from the project's published releases, counting the
  waiting period in minor lines.
- Fail loudly on an unrecognized mark, rather than reading it as "not withdrawn".
- Report an undeterminable history as undetermined; never as compliant.
- Keep the no-import invariant intact — the check still audits the working tree, never an
  installed distribution.

**Non-Goals:**

- Any change to `src/spoc/`. The existing withdrawal is the fixture, and must keep passing.
- A committed surface-record artifact. See Decisions.
- Judging whether a stated replacement is *good*. As `states_settling_condition` already
  documents for the provisional case, only the bare omission is mechanically detectable.
- Changing the pre-stable allowance, or the release at which enforcement begins.

## Decisions

Core and adapters follow the package's existing split, unchanged in direction: `core.py`
is pure and learns nothing about where facts came from; `extract.py` reaches for source,
`release.py` reaches for published releases, `cli.py` and `diffcli.py` translate and
render only. All new reaching-out lands in the two existing adapters; all new judgement
lands in the core.

```
   diffcli.py / cli.py     thin entry points, no judgement
          |
          v
       core.py             Exposure.withdrawal, lifecycle verdict, findings   [pure]
          ^         ^
          |         |
    extract.py    release.py
    (source)      (published releases)
```

### Withdrawal is a field, not a tier

`Exposure` gains a `withdrawal: Withdrawal | None`, where `Withdrawal` carries the mark's
message and whether that message names a replacement. `Tier` is untouched.

*Alternative rejected:* a fourth `Tier` member, `DEPRECATED`. It reads naturally and is
wrong: `surface_delta` would report `retiered: X (public -> deprecated)` at the marking
release, which drops the promise a full release before the removal that the waiting period
exists to give consumers time for. The tier is what we promise; withdrawal is where the
element sits on the way out. They are orthogonal and must stay so.

### The mark is recognized syntactically; the prose is not a second input

**Critical concern — reading the withdrawal mark without executing the package.**
Decided: **Extend** griffe with a stdlib `ast` pass — see *Reading the withdrawal mark from
source* in `DECISIONS.md` (approved). Griffe supplies the module model and the file
inventory; recognizing *our own* mark on top of it is a project-specific rule with no
upstream to adopt. The one purpose-built candidate, `memestra`, is hard-rejected on
maintenance and solves the inverse problem.

The sanctioned mark is anything routed through `spoc.core.deprecation` — today
`deprecated_alias(target, message)` at module level, and `@deprecated(message)` for a
definition. Both are recognized, and the message literal is read with it, which is what
makes "names a replacement, or says there is none" checkable.

*Alternative rejected:* also requiring a prose notice in the documentation, mirroring
`PROVISIONAL_NOTICE`. The two cases are not symmetric. For `provisional`, the
documentation *is* the promise — there is no runtime mechanism it could otherwise live in.
For withdrawal, the promise is the runtime signal, and the mark already carries its own
message as a string literal, so the prose adds no fact and adds a second place to drift.
The `#:` comment above the existing mark stays as documentation; it is not a gate input.

*Alternative rejected:* importing the package and observing the warning. It would be the
most direct evidence, and it breaks the invariant that makes this tool trustworthy — a
checker that imports its subject audits whatever happens to be installed. `diffcli` already
passes `allow_inspection=False` for the same reason.

*Consequence — a false pass in the one direction that matters.* A mark spelled some third
way reads as "not withdrawn", and an element with no lifecycle at all reads identically.
The mitigation is not redundancy but closing the other end: `src/spoc/core/deprecation.py`
already declares itself "the one import site for the deprecation signal," so the check
reports any `DeprecationWarning` raised outside it as an unsanctioned mark. That converts
a silent false pass into a finding, and it enforces a rule the module already claims.

### History comes from the published releases, walked lazily

**Critical concern — reconstructing per-release history.** Decided: **Extend**
`apicheck.release` — see *Reconstructing per-release history* in `DECISIONS.md` (approved).
It already materializes a ref's `src/` and hands it to the ordinary extractor. No new
dependency and no new artifact; griffe's `load_git` was considered and rejected because it
would introduce a second way of reading a ref.

The walk is driven by removals, not run unconditionally: only an element that
`surface_delta` reports as `REMOVED` with `promises == True` triggers it, and the walk
stops at the first release where the element is present without a mark. In the ordinary
case — nothing promised was removed — it costs nothing at all.

Releases are ordered by parsed version, not by tag creation date, and grouped into minor
lines, because the policy counts minor releases. Eight of the twelve current tags are
patches (`v0.3.2`…`v0.3.9`); counting tags instead of minor lines would let a patch release
satisfy a waiting period the policy measures in minors.

Both sides are read through the same extractor `release.py` already routes through, so an
element cannot be judged withdrawn at one release and merely absent at another because they
were observed differently.

*Alternative rejected:* a committed surface record — a generated, per-release file the gate
reads instead of recomputing, with griffe's own JSON dump as the natural format since it
round-trips `deprecated`. Its whole appeal is avoiding N loads, and lazy walking makes N
zero in the common case. A record is a cache of what the repository already holds, and it
adds an artifact that can drift from its source. Revisit only if the walk becomes slow.

### Where the mark is read from

The message spans two implicitly concatenated string literals, so the value has to survive
real parsing rather than a regex. `extract.py` already opens and reads every source file
for `#:` comment blocks; the mark is derived from a parse of those same files, and both
facts come out of one pass over the source.

*Trade-off:* this puts a second reading technique beside the existing line scan. Folding
the `#:` reader onto the same parse is the coherent end state (Rule 7) but is not required
by this change; it is noted as a follow-up rather than done blind.

### Which findings are fatal, and when

The split follows the requirement each finding serves, not a single switch:

| Finding | Fatal |
| --- | --- |
| mark names no replacement and does not say there is none | immediately |
| withdrawal signal outside the sanctioned mechanism | immediately |
| removal without a completed lifecycle | from 1.0 |
| withdrawal history undeterminable | never a pass; non-zero from 1.0 |

The first two are properties of the working tree and have nothing to do with the
pre-stable allowance, which permits *breaking changes* before 1.0, not badly written
marks. The third is exactly what the allowance permits, so failing on it now would make
the gate contradict the policy — the same reasoning already written into `diffcli`'s
docstring. This adds no new spec requirement; it follows from the allowance already in
`release-policy`.

For exit codes, an undeterminable history reuses `diffcli`'s existing `2` — the code that
already means "the comparison did not happen," which must never read like a comparison
that found nothing. Violations use `1`.

### The increment is weighed, not just the change

Found while implementing, and decided in scope rather than deferred. `diffcli` failed on
*any* breakage once past 1.0, regardless of which increment was claimed. Since a removal
is always a breakage, that rule made a compliant major release impossible to cut: the very
release the lifecycle exists to earn could never pass its own gate, and `2.0.0` could
never ship at all.

So from 1.0 the exit rule reads the increment. An incompatible change is what a major
release *is*, so breakages are permitted when the declared version's major exceeds the
baseline tag's and refused in every other increment. An incomplete withdrawal stays fatal
in every increment — a major release may remove a `public` element, but it may not skip
the lifecycle that earns the removal. A baseline ref that is not a released tag yields no
version, and is treated as "the increment cannot be established" rather than as any
particular one, because guessing there would decide whether a breaking change is allowed.

This is the one place the change touched pre-existing logic. It is here because the spec
scenario *a completed lifecycle passes* is not satisfiable without it.

## Risks / Trade-offs

- **An unrecognized mark reads as no mark.** → The unsanctioned-signal check closes the
  common escape (a hand-rolled `warnings.warn`), and the sanctioned mechanism is a single
  module that already says so in its own docstring.
- **The first enforcement event is the one that matters, and it is 1.0.** Every rule here
  is reported from the day it lands but only fatal later, so the path from "reported" to
  "enforced" is never exercised until the release it is meant to protect. → The tests
  exercise the post-1.0 behavior directly against synthetic version values rather than
  waiting for 1.0, and the existing withdrawal in `spoc.scaffold` is carried as a live
  fixture through the marking release.
- **The walk cannot see before the oldest available tag.** An element marked at the oldest
  tag, with too few minor lines after it, is genuinely undeterminable. → Reported as
  undetermined, which is not a pass. A shallow CI checkout hits this the same way
  `latest_tag` already does, and gets the same kind of message.
- **Tag ordering changes meaning.** `latest_tag` sorts by creation date; the walk sorts by
  parsed version. A retagged or back-dated release could make the two disagree. → The walk
  uses version order throughout and never mixes the two; the divergence is recorded here so
  a later reader does not "fix" one to match the other.
- **Message-content checking is prose pattern-matching.** "Names a replacement" cannot be
  decided mechanically in general. → Accepted, on the same reasoning
  `states_settling_condition` already records: the real failure is nobody writing the
  sentence at all, and that is detectable.

## Open Questions

- ~~Should the unsanctioned-signal check scan the whole of `src/`, or only modules that
  contribute exposed elements?~~ **Decided while implementing: the whole of `src/`.** A
  `DeprecationWarning` raised from an internal module still reaches a consumer at runtime,
  and the failure being prevented — an unrecognized mark reported as no mark — does not
  respect the boundary of the published surface.
- The `#:` comment reader and the new parse both walk every source file. Consolidating them
  is clearly right and is deliberately out of scope here; it should be a follow-up rather
  than a second concern inside this change.
- PEP 842 (draft, targeting 3.16) proposes `ExportWarning` for reaching an unexported
  module attribute. If it lands, "internal but importable" and "withdrawn re-export" become
  language-level distinctions and this recognition rule should be revisited against the
  standard (Rule 9) rather than diverging from it by inattention. Carried forward from
  `decide-scaffold-surface`.
