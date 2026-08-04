# Rule 3 — Commit in logical batches (Conventional Commits)

**Trigger:** after any task or opsx operation that creates or significantly modifies files.

Do the whole cycle unprompted — the user tracks progress through branches, not by running git.

## Branch and merge order per change

Work happens on a per-change branch so each change is trackable:

`/opsx:apply` → **commit** the implementation → `/opsx:sync` → `/opsx:archive` →
**commit** the sync/archive delta → **merge the branch into `main`**.

Fold into `main` only after archive. Merging is a review, not a text operation — Rule 4.

## Before committing

1. Review the full diff (`git status` + `git diff`). **Never commit blind.**
2. Split changes into commits by coherent intent — stage per-path or with `git add -p` as needed.
3. Use Conventional Commit types: `feat`, `fix`, `refactor`, `docs`, `test`, `build`, `ci`,
   `perf`, `chore`.

## Each commit must

- Represent one coherent change, understandable on its own from its message.
- Not mix unrelated concerns.
- Leave the repository in a valid (building, ideally passing) state wherever practical.

Example sequence for one feature:

```
feat: add user authentication flow
test: add authentication integration tests
refactor: extract authentication provider adapter
docs: document authentication architecture
```

Prefer several small meaningful commits over one "misc changes" commit. Never let large
unrelated changes accumulate uncommitted across tasks.

## Attribution — never

Commits carry the user's account only. Do **not** add `Co-Authored-By:` trailers, a
"Generated with Claude Code" line, or any other attribution — not on commits, not on merges,
not in PR bodies. Author = the user, full stop.

Keep the message about the change itself: no marketing, no self-congratulation, no restating
the diff line by line.
