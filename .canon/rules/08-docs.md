# Rule 8 — Documentation is part of the implementation

**Trigger:** any change to architecture, data flow, public APIs, domain boundaries, deployment
topology, or a significant workflow.

Documentation that contradicts the implementation is a **defect**, with the same severity as a
failing test. It is worse than absent documentation, because it is trusted.

## Do

- Update the relevant docs and diagrams **in the same logical change set** — the same branch
  and merge. It may be its own `docs:` commit (Rule 3), but it does not slip to "later".
- During Rule 6 validation, verify the docs still describe the system accurately.
- If a doc genuinely cannot be updated in the same change set, leave an explicit tracked TODO
  **and say so in the report**. Never silently.

Which doc, and where it lives, follows the routing table in `CLAUDE.md` and the document
taxonomy in `.canon/guidelines.md`. Diagrams follow Rule 1.
