# Rule 1 — Diagram architecture with Mermaid

**Trigger:** explaining, designing, or changing system architecture, data flow, service
communication, request lifecycles, event workflows, state machines, DB relationships, or
deployment topology.

## Do

- Produce a Mermaid diagram instead of long prose whenever a visual is clearer.
- Store diagrams next to the docs they belong to — `docs/architecture/` is the default home —
  in fenced ` ```mermaid ` blocks so they render in Git hosting.
- Update affected diagrams **in the same change set** as the code change (Rule 8).

## Constraints

- Diagrams describe the **current** implementation. An aspirational design must be explicitly
  labeled "proposed" or it is a lie about the system.
- One concern per diagram. Split rather than cram.
- Validate the syntax before committing — a diagram that fails to render is worse than none.

## Where diagrams live

`docs/architecture/` is committed and canonical. `.ai_notes/` is gitignored scratch and is
**not** a home for anything durable — a diagram left there is lost work. This extends the
routing table in `CLAUDE.md`: an architecture diagram of the current system is a durable
artifact, so it gets promoted, never parked.
