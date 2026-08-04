# Rule 4 — Treat merges as reviewed integrations, not text operations

**Trigger:** any branch merge.

A clean merge (no textual conflicts) does **not** mean a correct integration. There is no human
reviewer in the loop — you are the reviewer. Treat every merge as a pull request you must
approve.

## Before finalizing

1. Read each branch's changes and understand the _intent_ behind them —
   `git log` and `git diff base...branch`, not just the conflict list.
2. Identify overlapping, duplicate, or competing implementations of the same capability.
3. Detect divergent naming, patterns, and incompatible assumptions.
4. Resolve design conflicts deliberately: pick the strongest, most coherent implementation
   (Rule 7). Don't keep both.
5. Hunt **semantic conflicts** — changes that each work alone but break combined. The classic:
   one branch renames what the other branch calls. Git reports nothing.
6. Delete the superseded code from the losing side.
7. Run the full validation suite (Rule 6) **on the merged result**, not on either branch.
8. Read the final integrated diff as one system before committing the merge.

Then clean up — Rule 5.
