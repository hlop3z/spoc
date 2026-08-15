# The Canon

The rules this project actually lives by. **Ours** — authored here, owned here, independent
of every external tool.

## Why this folder exists

Workflow tooling comes and goes — one change-tracking system has already been adopted,
outgrown, and removed from this repository. Nothing that matters may live only in a
folder some tool can overwrite or a migration can delete, so the canon lives here,
owned directly, and whatever tooling is in use points _into_ it.

## Precedence

**`.canon/` comes first.** When any tool's or workflow's instructions conflict with a
rule here, the rule here wins — say so out loud rather than silently following the tool.
A condensed projection of these rules may live wherever a tool requires one; it is
re-derived from here, never the reverse, and an edit to a projection is never a rule's
only home.

## What's here

- **`rules/`** — the numbered engineering rules. Imperative and trigger-based: each states
  when it fires and what to do.
- **`guidelines.md`** — the reference the rules cite: build-vs-adopt hierarchy, maturity
  rubric, abstraction layers, file-size thresholds, doc taxonomy.
- **`checks.md`** — this project's canonical validation commands (Rule 6). Per-project; the
  template ships it nearly empty.

Where a change's documentation belongs is decided by the doc taxonomy in `guidelines.md`;
decision records go to `DECISIONS.md` at the repository root.

## Lifecycle

A rule earns its place by changing behavior. If a rule never fires, delete it; this is a canon,
not an archive. Rules are cited by number ("Rule 3"), so renumbering is a breaking change —
append rather than insert.
