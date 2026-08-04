# The Canon

The rules this project actually lives by. **Ours** — authored here, owned here, independent
of every external tool.

## Why this folder exists

`openspec/` belongs to the OpenSpec CLI, and `.claude/commands/opsx/` is vendored from it.
Both can be reinstalled, upgraded, or regenerated at any time. Nothing that matters may live
only in a folder someone else can overwrite.

So the canon lives here and external tooling points _into_ it. Reinstalling OpenSpec touches
`openspec/` and `.claude/commands/opsx/` — never `.canon/`.

## Precedence

1. **`.canon/`** — these rules come first. When an opsx command's instructions conflict with
   a rule here, the rule here wins. Say so out loud rather than silently following the command.
2. **`openspec/config.yaml`** — a _bridge_: the content is ours, the location and schema are
   OpenSpec's. It condenses this canon for injection into generated artifacts. If a reinstall
   overwrites it, re-derive it from here — never the reverse.
3. **`.claude/commands/opsx/`** — vendored, regenerable, expendable. An edit there is never a
   rule's only home.

## What's here

- **`rules/`** — the numbered engineering rules. Imperative and trigger-based: each states
  when it fires and what to do.
- **`guidelines.md`** — the reference the rules cite: build-vs-adopt hierarchy, maturity
  rubric, abstraction layers, file-size thresholds, doc taxonomy.
- **`checks.md`** — this project's canonical validation commands (Rule 6). Per-project; the
  template ships it nearly empty.

The trigger index lives in `CLAUDE.md`, which loads every session. It is not duplicated here —
one index, one home.

## Lifecycle

A rule earns its place by changing behavior. If a rule never fires, delete it; this is a canon,
not an archive. Rules are cited by number ("Rule 3"), so renumbering is a breaking change —
append rather than insert.
