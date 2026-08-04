---
name: "AI: Handoff"
description: "Generate a HANDOFF.md snapshot of session state for cross-session continuity"
category: AI
tags: [ai, session, handoff, continuity]
---

Generate a `HANDOFF.md` at the project root that snapshots the current session so a future
session can resume without context loss.

**This is a snapshot, not a log.** Each run produces the current state of the world — it is
a resume note for picking your own work back up, not a historical record.

## Hard rules

1. **Overwrite, never append.** If `HANDOFF.md` already exists, replace it entirely. Never
   accumulate prior sessions' content — an append-mode file rots and contradicts itself.
2. **Reference, never duplicate.** For anything that already has a canonical home, write a
   pointer to that home — do not copy its contents. This preserves single source of truth
   and keeps the snapshot from drifting:
   - Active changes → `openspec list` (name them, link to `openspec/changes/<name>/`)
   - Open work → the relevant `tasks.md`
   - Decisions + rationale → the relevant `design.md` ADR section
   - Durable facts about the user/project → the memory dir
3. **Only capture what has no other home.** Free-form prose is restricted to the three
   things below. Everything else is a reference.
4. **Gitignored.** Ensure `HANDOFF.md` is in `.gitignore`; add it if missing. The snapshot
   is a private resume note, not a committed canonical home.
5. **Promote, don't hoard.** If the session produced a durable finding (a decision, a spec,
   a fact), promote it to its proper home — don't let `HANDOFF.md` become its storage.

## Steps

1. Run `openspec list --json` (if the project uses OpenSpec) to enumerate active changes to
   reference. Skip silently if not an OpenSpec project.
2. Check `.gitignore` for `HANDOFF.md`; add the entry if absent.
3. Write `HANDOFF.md` at the project root using the structure below, OVERWRITING any
   existing file.
4. Report the path written and confirm it is gitignored.

## HANDOFF.md structure

```markdown
# Handoff

> Session snapshot — overwritten each run. Resume state only; canonical content lives in
> the linked sources, not here.

## Session narrative

<!-- What this session was about and what got done, across changes. The story that no
     single tasks.md or design.md tells. Keep it tight. -->

## Current state / where work stopped

<!-- In-flight state: what is half-done, what is blocked, the exact point work paused. -->

## Next steps

<!-- The recommended next actions for the future session, in priority order. -->

## References

<!-- Pointers ONLY — no copied content.
     - Active changes: openspec/changes/<name>/
     - Open work: <path>/tasks.md
     - Decisions: <path>/design.md
     - Durable facts: memory/ -->
```

## Guardrails

- Any content duplicated from a canonical home is a defect — replace it with a reference.
- If there is genuinely nothing in-flight, say so plainly rather than padding the snapshot.
- Do not invent state; only record what actually happened this session.
