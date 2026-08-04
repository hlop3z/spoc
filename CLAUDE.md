# How to develop here

This project drives all work through **OpenSpec**, governed by a canon of engineering rules
that is ours and comes first. Follow the pipeline — the rules apply themselves.

```
/opsx:explore   Think it through. Decompose (invariants, boundaries, ≥3 strategies). No code.
      ↓
/opsx:propose   Generate proposal.md (WHY/scope) + specs (abstract WHAT) + design.md (HOW).
      ↓
/ai:decide      Build-vs-adopt gate: per critical concern, Rent>Adopt>Extend>Fork>Build.
      ↓             Records each decision into design.md. Run before implementing.
/opsx:apply     Implement the tasks. Thin entry points; adapters isolate every dependency.
      ↓
/opsx:sync      Fold the change's delta specs into the main specs.
      ↓
/opsx:archive   Close out the completed change.
```

## The canon comes first

`.canon/` holds the rules this project lives by. It is **ours** — no external tool writes
there. When an opsx command's instructions conflict with a rule in `.canon/`, the rule wins;
say so rather than silently following the command. See `.canon/README.md` for the full
precedence and ownership contract.

## The rules (open the file when the trigger fires)

| #                                    | Trigger                              | In one line                                                                       |
| ------------------------------------ | ------------------------------------ | --------------------------------------------------------------------------------- |
| [1](.canon/rules/01-diagrams.md)     | explaining or changing architecture  | Draw it in Mermaid, in `docs/architecture/`, describing what _is_.                |
| [2](.canon/rules/02-architecture.md) | code touching any external system    | Pure core, ports and adapters at the boundary; dependencies point inward.         |
| [3](.canon/rules/03-commits.md)      | finishing any multi-file task        | Review the diff, split by intent, Conventional Commits, never co-author.          |
| [4](.canon/rules/04-merges.md)       | any branch merge                     | A clean merge is not a correct one — you are the reviewer.                        |
| [5](.canon/rules/05-cleanup.md)      | a merge just landed                  | Delete what the merge superseded; git history is the history.                     |
| [6](.canon/rules/06-validation.md)   | about to claim something is done     | Run the checks in `.canon/checks.md`; report what you couldn't run as unverified. |
| [7](.canon/rules/07-coherence.md)    | code sits beside an existing pattern | Coherence beats minimal diff; consolidate duplicates, flag out-of-scope mess.     |
| [8](.canon/rules/08-docs.md)         | architecture or API changed          | Docs that contradict the code are defects — same change set, not later.           |
| [9](.canon/rules/09-standards.md)    | defining schemas, IDs, vocabularies  | Adopt the global standard: JSON Schema/OpenAPI/AsyncAPI; Wikidata/DOI/ORCID/LEI + UUID; Schema.org/RDF/ISO. |
| [10](.canon/rules/10-system-shape.md) | starting a system or bounded context | Modular monolith on a kernel by default; DDD contexts, events between them, reads split from writes. |
| [11](.canon/rules/11-object-registry.md) | naming or registering system objects | One grammar — `kind:namespace.object_name`, lowercase snake_case — in one kernel registry that every projection derives from. |

## The two ideas that make this work

1. **Abstraction layers stay separate.** WHAT (`specs/`) is language-agnostic behavior.
   HOW (`design.md`) is structure + tool choices. DO (`tasks.md` + code) is the implementation.
   No layer leaks into another. Core holds behavior; every surface is a thin adapter (Rule 2).

2. **Never reinvent the wheel.** If a mature tool already does the job, adopt it — do not
   write your own. This applies to whole CLIs, not just libraries: before building anything,
   search for what already exists. `/ai:decide` makes the call explicit and records it, and
   `scripts/go/cmd/ensure` installs an adopted tool so "it isn't installed" is never the
   reason to rebuild it.

   > This rule has already been violated once in this repo: a `loc` line-counter was written
   > from scratch when `tokei` and `scc` both existed. It was deleted and replaced. Searching
   > first costs a minute; the rebuild cost a day and shipped a bug the mature tool never had.

## Where the rules live (don't restate them)

- **`.canon/rules/`** — the canon above. Imperative, trigger-based.
- **`.canon/guidelines.md`** — the full reference: build-vs-adopt hierarchy, maturity rubric,
  abstraction layers, file-size thresholds, doc taxonomy.
- **`.canon/checks.md`** — this project's validation commands.
- **`DECISIONS.md`** — build-vs-adopt ADRs recorded by `/ai:decide`.
- **`scripts/README.md`** — the tool workshop: Go, Python, and legacy shell environments.
- **`openspec/config.yaml`** — a bridge file: our philosophy, condensed into the schema the
  OpenSpec CLI injects into every artifact. Derived from `.canon/`, never the reverse.

Commands stay thin and point at these, so a change costs few tokens to plan.

## File ownership (`.canon/` and `ai:` are ours, `opsx:` is upstream)

- **`.canon/`** — ours. The canon. No external tool may write here.
- **`.claude/commands/ai/`** — ours. Lives under `.claude/` only because the harness requires
  that location. Must degrade gracefully when OpenSpec is absent — no `ai:` command may
  hard-fail because `openspec` isn't installed.
- **`openspec/config.yaml`** — bridge: content ours, location and schema theirs. If a reinstall
  overwrites it, re-derive from `.canon/`.
- **`.claude/commands/opsx/`** and the rest of `openspec/` — vendored from the OpenSpec CLI.
  **Regenerable**: an upgrade may overwrite them, so any edit there is expendable and must
  never be a rule's only home.

New custom command → `.claude/commands/ai/`. New rule → `.canon/rules/`.

## Keep the main thread cheap

For broad or exploratory searches — locating code across many files, surveying naming
conventions, answering a question that spans several files — delegate to the `Explore` or
`general-purpose` subagent and keep only its conclusion. Don't read the file dumps into the
main thread. For a single known file or symbol, just search directly (a subagent would cost
more than it saves).

## Where findings go (promote or discard — never accumulate)

There is **no `/research` folder**. A global, ever-growing notes dump rots and starts
misleading. Every durable finding gets exactly one canonical home; everything else dies in
the scratchpad. When a subagent surfaces something worth keeping, route it:

- **Throwaway exploration** → the session scratchpad. Auto-discarded; never committed.
- **Derivable from code** → leave it in the code. Don't snapshot it.
- **A decision + its why** (build-vs-adopt, tradeoffs) → `design.md` ADR block.
- **Durable behavior contract** → `specs/` (synced to main specs on `/opsx:sync`).
- **How the system is shaped** → a Mermaid diagram in `docs/architecture/` (Rule 1).
- **A rule about how we work** → `.canon/rules/`.
- **A repeatable operation** → a CLI tool in `scripts/` via `/ai:tool` — not a shell one-liner
  you retype. Disposable experiments go to `scripts/py/lab/` and get pruned.
- **In-flight notes for a specific change** → `openspec/changes/<change>/`, archived on `/opsx:archive`.
- **Non-derivable fact about the user/project** → the memory dir; update or delete when wrong.

The discipline is promote-or-discard, not save-more: one home, one lifecycle, one owner.
