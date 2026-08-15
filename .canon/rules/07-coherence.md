# Rule 7 — Coherent architecture beats minimal change

**Trigger:** integrating or modifying code that sits alongside an existing pattern.

Do not preserve a pattern merely because it exists, if it contradicts the intended
architecture. "It was already like that" is not a justification.

## Priority order when choices conflict

1. Correctness
2. Architectural consistency (Rule 2)
3. Maintainability
4. Testability
5. Clear separation of concerns
6. Minimal unnecessary complexity

## Consolidate

When two implementations solve the same problem, collapse them into one. Parallel versions may
exist only with a deliberate, documented reason — a labeled migration period with a removal
plan, recorded as a decision in `DECISIONS.md`, not an accident left in place.

## Scope discipline

Consolidate what the task touches. Large inconsistencies **outside** the task's scope get
flagged, never silently rewritten — an unrequested refactor buried in a feature diff is
unreviewable, and it violates Rule 3's one-coherent-change-per-commit.
