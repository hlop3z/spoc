# Rule 5 — Clean up after every merge

**Trigger:** a branch has been integrated, before declaring the merge done.

- [ ] Remove obsolete and duplicate implementations.
- [ ] Remove unused imports, dependencies, dead files, and abandoned experiments.
- [ ] Resolve temporary compatibility shims that are no longer needed.
- [ ] Update documentation and diagrams to the merged reality (Rules 1 and 8).
- [ ] Update tests affected by the final architecture.
- [ ] Grep for merge artifacts: `<<<<<<<`, `TODO(merge)`, `_old`, `_backup`, `.orig`.

Do not preserve redundant code just because it existed on one branch. The repository
represents the intended architecture, not a history of attempts — **git history is the
history.**
