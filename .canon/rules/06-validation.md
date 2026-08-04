# Rule 6 — Validate before claiming done

**Trigger:** before considering any operation complete.

Run everything applicable to this repository. The canonical commands are in
`.canon/checks.md` — use those exact commands, and add any that are missing once discovered.

- [ ] Formatter
- [ ] Linter
- [ ] Type checker
- [ ] Unit tests
- [ ] Integration tests
- [ ] Build / compilation
- [ ] Inspect the final `git diff`
- [ ] Verify generated artifacts are correct, or correctly ignored
- [ ] Confirm architecture docs and diagrams still match the code (Rule 8)

## Honesty

- A check that **cannot** run — missing tooling, no network, no database — is reported as
  **unverified**, by name. Never imply it passed.
- Never claim completion from "no git conflicts" or "the files were written". Neither is
  evidence that anything works.
- A failing check gets fixed or reported. Never buried, never softened.

State what you actually ran. "Tests pass" when you ran the formatter is a false report, and it
is the most expensive kind of error here — every later decision inherits it.
