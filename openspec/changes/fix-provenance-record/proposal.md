## Why

The `template-provenance` spec requires that *"a project generation MUST emit a record of the
template set reference it was generated from"* — unconditionally, for every generation. The
implementation does not honour that: the record lands on disk only because the built-in template
set happens to declare it among its files. A template set that omits that declaration produces a
project with **no provenance at all** — which is precisely the third-party, remote-reference case
provenance exists to serve. The single guarantee that survives a set the author did not write is
the one guarantee the set can silently drop.

Nothing crashes today, because an absent record degrades to "this project records no origin".
But the published behaviour (`docs/docs/tools/cli.md`: *"Every generated project also gets a
`.spoc-template.toml`"*) is false for any set but the built-in one, disproved by a live run.
That is both a spec-conformance defect and a docs defect. The same pass settles the three open
questions the preceding change deliberately deferred, so provenance stops carrying unfinished
business.

## What Changes

- The origin record becomes **scaffolder-authored**, not template-declared. The scaffolding
  operation contributes it to the generation plan itself, so every generated project carries it
  regardless of which template set was rendered or who wrote that set.
- The record's path becomes a **reserved target**. A template set may no longer declare a file
  that lands there — the set cannot suppress the record, and equally cannot forge or overwrite
  it with content of its own choosing. A set that declares it is refused by the same validation
  that already rejects an incomplete set, naming what is reserved and why.
- The built-in template set stops declaring the record and stops carrying its template file;
  it becomes an ordinary set with no privileged relationship to provenance.
- The three substitution values that exist only to feed the record
  (`template_reference`, `template_revision`, `template_set_name`) leave the substitution
  vocabulary — they are no longer values a template set may consume.
- The record becomes **JSON** (`.spoc-template.json`) rather than TOML. Added after `/ai:decide`
  found a second live defect: the record's values are arbitrary caller-supplied strings, and the
  current TOML template neither escapes nor quotes them, so a reference containing a backslash
  (any Windows directory path) or a quote produces an unparseable record — which `read_origin`
  reports as "no origin". Emitting TOML correctly means hand-rolling escaping for a format on
  the never-hand-roll list, or a base dependency for one advisory file. See `DECISIONS.md`.
- A failed remote retrieval names the reference **as the author supplied it** rather than the
  location the scaffolder derived from it.
- The three open questions carried over from `remote-template-sources` are answered in this
  change's design and closed:
  1. Does the record belong in the project's configuration file instead of its own file?
  2. Should the built-in set record an origin, or is the record only meaningful for references
     that can move?
  3. Should adding an app *refuse* rather than warn when the recorded origin diverges and the
     kinds were derived rather than stated?
- `docs/docs/tools/cli.md` is corrected in the same change set, so the promise it makes and the
  behaviour agree (Rule 8).

Not breaking in any way that reaches a user: no project consumes this record at runtime, and no
template set outside this repository declares the reserved target. A project generated before
this change keeps an inert `.spoc-template.toml` that nothing reads — it reports "no origin",
which is the documented degradation.

## Capabilities

### New Capabilities

None. This change closes a gap between an existing contract and its implementation, and hardens
that contract against a case it did not previously state.

### Modified Capabilities

- `template-provenance`: the record's **authorship** becomes part of the contract. Emission is
  the scaffolding operation's obligation and is independent of the rendered template set's
  declared shape; a template set can neither suppress the record nor supply its content.
- `scaffold-templates`: a template set's declared shape gains a **reserved target** it may not
  claim, refused by the existing pre-write validation. The declared substitution vocabulary
  correspondingly loses the values that only fed the record.
- `remote-template-acquisition`: a retrieval failure must name the reference in the form the
  caller supplied, not a location derived from it — the caller can only act on what they wrote.

**Critical concern for `/ai:decide`**: this change puts a value in the generated project that a
downstream party (a remote template set author) must not be able to influence. Whether that
integrity boundary is enforced by construction (the record never passes through template
rendering) or by validation (a reserved-name check) is a build-vs-adopt call to record before
implementing.

## Impact

- **Core operation**: `src/spoc/scaffold/operations.py` — `init_project` gains the record as its
  own contribution to the plan; the three record-only substitution values leave `values`.
- **Provenance module**: `src/spoc/scaffold/provenance.py` — gains the write side (it currently
  only reads), so the record's shape is defined once, next to the code that parses it; switches
  both directions to `json`.
- **Template set validation**: `src/spoc/scaffold/core.py` / `plan.py` — the reserved-target
  rule, and a new error naming it.
- **Built-in template set**: `src/spoc/scaffold/templates/default/` — `manifest.toml` loses the
  record entry and the three values; `spoc-template.toml.tmpl` is deleted.
- **Remote adapter**: `src/spoc/scaffold/remote.py` — failures carry the supplied reference.
- **Docs**: `docs/docs/tools/cli.md` (the `.spoc-template.toml` promise), plus the template-set
  authoring docs wherever they enumerate substitution values or manifest rules.
- **Architecture**: `docs/architecture/scaffold-resolution.md` if the plan's composition changes
  shape (Rule 1).
- **Tests**: `tests/` — the case that fails today is generation from a set that declares no
  record; add it, plus the reserved-target refusal.
- **No dependency, distribution, or public API change.**
